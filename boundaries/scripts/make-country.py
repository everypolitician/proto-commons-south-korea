from shapely.geometry import MultiPolygon  # Polygon,  LinearRing
# import shapely
from shapely.geometry import shape, mapping
from shapely.geometry.polygon import orient
from shapely.ops import unary_union
import fiona
import fiona.crs
import fiona.transform
import itertools
import os


def dissolve_by_attribute(shp_file, attr, verbose=0, simplify=0):
    """
    Takes an open fiona collection of features and the name of an attribute.
    Returns a list of features dissolved based on common values of attr.
    """
    dissolved_features = []
    feat_sorted = sorted(shp_file,
                         key=lambda k: k['properties'][attr])
    for key, group in itertools.groupby(feat_sorted,
                                        key=lambda k: k['properties'][attr]):
        attr_value = key

        # This could be improved by only buffering invalid geoms.
        if simplify:
            geoms = [shape(feature['geometry']).simplify(
                100, preserve_topology=True).buffer(0.0) for feature in group]
        else:
            geoms = [shape(feature['geometry']).buffer(0.0) for feature in group]

        # clean_geoms = [zero_buffer(s) for s in geoms]
        if verbose:
            print('dissolving {} features into {}'.format(len(geoms), key))
        dissolved_geom = mapping(unary_union(geoms))
        dissolved_feature = {'geometry': dissolved_geom,
                             'properties': {attr: attr_value}}
        dissolved_features.append(dissolved_feature)

    return dissolved_features


def dissolve(shp_file, verbose=0, simplify=0):
    """
    Takes an open fiona collection of features.properties
    Returns a single dissolved geometry.
    """
    if simplify:
        geoms = [shape(feature['geometry']).simplify(
            simplify,
            preserve_topology=True).buffer(0.0) for feature in shp_file]
    else:
        geoms = [shape(feature['geometry']).buffer(0.0) for feature in shp_file]

    if verbose:
        print('dissolving {} features'.format(len(geoms)))
    dissolved_geom = mapping(unary_union(geoms))
    return dissolved_geom


def generate_attributes():
    attributes = {
        'NAME': '대한민국',
        'NAME_EN': 'Republic of Korea',
        'MS_FB': 'country:kor',
        'WIKIDATA': 'Q884'
    }
    return attributes


def orient_polygons(shp):
    if shp.geom_type == 'Polygon':
        return orient(shp)
    elif shp.geom_type == 'MultiPolygon':
        oriented_polygons = []
        for polygon in shp:
            oriented = orient_polygons(polygon)
            oriented_polygons.append(oriented)
        return MultiPolygon(oriented_polygons)
    else:
        print('shp is not a Polygon or a MultiPolygon')


def orient_feature(geometry):
    shp = shape(geometry)
    oriented_shp = orient_polygons(shp)
    return mapping(oriented_shp)


def transform_to_4326(geom, crs):
    return fiona.transform.transform_geom(crs, 'EPSG:4326', geom)


def eps_buffer(shp, eps):
    """take a feature and return a cleaned version"""
    geom = shape(shp)
    clean = geom.buffer(eps, resolution=5).buffer(-eps, resolution=5)
    return mapping(clean)


def filter_by_area(shp, threshold):
    if shp.geom_type == 'MultiPolygon':
        filtered_polygons = []
        for polygon in shp:
            filtered = filter_by_area(polygon, threshold)
            filtered_polygons.append(filtered)
        return MultiPolygon(filtered_polygons)
    elif shp.geom_type == 'Polygon':
        if shp.area > threshold:
            return shp
    else:
        print('{} is not of type "Polygon" or "MultiPolygon"'.format(shp))


def filter_feature_by_area(geometry, threshold):
    shp = shape(geometry)
    filtered_shp = filter_by_area(shp, threshold)
    return mapping(filtered_shp)


def make_country_shp(src_shp, country_out, src_crs,
                     out_properties={}, verbose=0, simplify=0):
    """"""
    with fiona.open(src_shp, 'r', encoding='EUC-KR', crs=sk_crs) as src:
        if verbose:
            print('src crs is {}'.format(src.crs))
            print('src schema is {}'.format(src.schema))

        out_schema = src.schema.copy()
        out_schema['properties'] = out_properties

        with fiona.open(country_out, 'w',
                        encoding='UTF-8',
                        driver='ESRI Shapefile',
                        schema=out_schema,
                        crs=fiona.crs.from_epsg(4326)) as output_shp:

            # Dissolve component geometries
            country_geom = dissolve(src, verbose=verbose, simplify=simplify)

            # make a feature to hold dissovled geom.
            country = {}
            country['geometry'] = country_geom

            # clean artefacts/slivers etc.
            country['geometry'] = eps_buffer(country_geom, 0.01)

            # Transform
            country['geometry'] = transform_to_4326(country['geometry'],
                                                    src_crs)

            # Orient
            country['geometry'] = orient_feature(country['geometry'])

            # Get attributes
            country['properties'] = generate_attributes()

            output_shp.write(country)


def make_temp(src_shp, temp_out, src_crs, verbose=0):
    with fiona.open(src_shp, 'r', encoding='EUC-KR', crs=sk_crs) as src:
        if verbose:
            print('src crs is {}'.format(src.crs))
            print('src schema is {}'.format(src.schema))
        meta = src.meta

        with fiona.open(temp_out, 'w', **meta) as temp_shp:

            for feature in src:

                # turn to shape and simplify
                geom = shape(feature['geometry'])

                # simplify
                geom = geom.simplify(5, preserve_topology=True)

                # re-turn to feature geometry
                feature['geometry'] = mapping(geom)

                # Orient
                feature['geometry'] = orient_feature(feature['geometry'])

                # zero buffer
                feature['geometry'] = shape(feature['geometry']).buffer(0.0)

                # remove small polygons.
                feature['geometry'] = filter_feature_by_area(feature['geometry'], 10)

                temp_shp.write(feature)


if __name__ == '__main__':

    src = '../source/Z_NGII_N3A_G0010000(12942)/Z_NGII_N3A_G0010000.shp'
    temp = '../build/country/country-temp.shp'
    country_out = '../build/country/country.shp'
    country_csv_out = '../build/country/country.csv'

    # values taken from http://spatialreference.org/ref/sr-org/grs80-korea-tm/
    # based on metadata
    sk_crs = {'k': 1, 'lat_0': 38, 'ellps': 'GRS80', 'proj': 'tmerc',
              'lon_0': 127, 'units': 'm', 'x_0': 200000, 'no_defs': True,
              'y_0': 500000}

    # make a temporary layer to filter small shapes
    make_temp(src_shp=src, temp_out=temp, src_crs=sk_crs, verbose=1)

    out_properties = {'NAME': 'str:100',
                      'NAME_EN': 'str:100',
                      'MS_FB': 'str:100',
                      'WIKIDATA': 'str:100'}

    make_country_shp(src_shp=temp,
                     country_out=country_out,
                     src_crs=sk_crs,
                     out_properties=out_properties,
                     verbose=1,
                     simplify=1)

    # delete temp
    os.remove('country.shp',
              'country.shx',
              'country.dbf',
              'country.cpg',
              'country.prj',
              dir_fd='../build/country')
