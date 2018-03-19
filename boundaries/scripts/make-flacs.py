from shapely.geometry import MultiPolygon  # Polygon,  LinearRing
# import shapely
from shapely.geometry import shape, mapping
from shapely.geometry.polygon import orient
from shapely.ops import unary_union
import fiona
import fiona.crs
import fiona.transform
import itertools


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


def dissolve(shp_file):
    """
    Takes an open fiona collection of features.properties
    Returns a single dissolved geometry.
    """
    geoms = [shape(feature['geometry']) for feature in shp_file]
    dissolved_geom = mapping(unary_union(geoms))

    return dissolved_geom


name_lookup = {
    '서울특별시': {
        'code': 'KR-11',
        'name_en': 'Seoul',
        'type': 'special-city'
    },
    '부산광역시': {
        'code': 'KR-26',
        'name_en': 'Busan',
        'type': 'met-city'
    },
    '대구광역시': {
        'code': 'KR-27',
        'name_en': 'Daegu',
        'type': 'met-city'
    },
    '인천광역시': {
        'code': 'KR-28',
        'name_en': 'Incheon',
        'type': 'met-city'
    },
    '광주광역시': {
        'code': 'KR-29',
        'name_en': 'Gwangju',
        'type': 'met-city'
    },
    '대전광역시': {
        'code': 'KR-30',
        'name_en': 'Daejeon',
        'type': 'met-city'
    },
    '울산광역시': {
        'code': 'KR-31',
        'name_en': 'Ulsan ',
        'type': 'met-city'
    },
    '세종특별자치시': {
        'code': 'KR-50',
        'name_en': 'Sejong Special Self-Governing City',
        'type': 'ssg-city'
    },
    '경기도': {
        'code': 'KR-41',
        'name_en': 'Gyeonggi-do',
        'type': 'province'
    },
    '강원도': {
        'code': 'KR-42',
        'name_en': 'Gangwon-do',
        'type': 'province'
    },
    '충청북도': {
        'code': 'KR-43',
        'name_en': 'Chungcheongbuk-do',
        'type': 'province'
    },
    '충청남도': {
        'code': 'KR-44',
        'name_en': 'Chungcheongnam-do',
        'type': 'province'
    },
    '전라북도': {
        'code': 'KR-45',
        'name_en': 'Jeollabuk-do',
        'type': 'province'
    },
    '전라남도': {
        'code': 'KR-46',
        'name_en': 'Jeollanam-do',
        'type': 'province'
    },
    '경상북도': {
        'code': 'KR-47',
        'name_en': 'Gyeongsangbuk-do',
        'type': 'province'
    },
    '경상남도': {
        'code': 'KR-48',
        'name_en': 'Gyeongsangnam-do',
        'type': 'province'
    },
    '제주특별자치도': {
        'code': 'KR-49',
        'name_en': 'Jeju Special Self-Governing Province',
        'type': 'ssg-province'
    }
}


def generate_attributes(name):
    id_type = name_lookup[name]['type']
    name_en = name_lookup[name]['name_en']
    iso_code = name_lookup[name]['code'].lower()

    attributes = {
        'NAME': name,
        'NAME_EN': name_en,
        'MS_FB': 'country:kr/{}:{}'.format(id_type, iso_code),
        'MS_FB_PARE': 'country:kr',
        'WIKIDATA': 'Q'
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


def make_flacs_shp(flacs_src, flacs_out, src_crs,
                   out_properties={}, verbose=0, simplify=0):
    """"""
    with fiona.open(flacs_src, 'r', encoding='EUC-KR', crs=sk_crs) as src:
        if verbose:
            print('src crs is {}'.format(src.crs))
            print('src schema is {}'.format(src.schema))

        out_schema = src.schema.copy()
        out_schema['properties'] = out_properties

        with fiona.open(flacs_out, 'w',
                        encoding='UTF-8',
                        driver='ESRI Shapefile',
                        schema=out_schema,
                        crs=fiona.crs.from_epsg(4326)) as output_shp:

            flacs = dissolve_by_attribute(src,
                                          'NAME',
                                          verbose=verbose,
                                          simplify=simplify)
            for f in flacs:
                f['geometry'] = fiona.transform.transform_geom(src_crs,
                                                               'EPSG:4326',
                                                               f['geometry'])

                f['geometry'] = orient_feature(f['geometry'])

                # This step could be broken out into separate areas.
                f['properties'] = generate_attributes(f['properties']['NAME'])

                output_shp.write(f)


if __name__ == '__main__':

    flacs_src = '../source/Z_NGII_N3A_G0010000(12942)/Z_NGII_N3A_G0010000.shp'
    flacs_out = '../build/flacs/flacs.shp'
    flacs_csv_out = '../build/flacs/flacs.csv'

    # values taken from http://spatialreference.org/ref/sr-org/grs80-korea-tm/
    # based on metadata
    sk_crs = {'k': 1, 'lat_0': 38, 'ellps': 'GRS80', 'proj': 'tmerc',
              'lon_0': 127, 'units': 'm', 'x_0': 200000, 'no_defs': True,
              'y_0': 500000}

    out_properties = {'NAME': 'str:100',
                      'NAME_EN': 'str:100',
                      'MS_FB': 'str:100',
                      'MS_FB_PARE': 'str:100',
                      'WIKIDATA': 'str:100'}

    make_flacs_shp(flacs_src=flacs_src,
                   flacs_out=flacs_out,
                   src_crs=sk_crs,
                   out_properties=out_properties,
                   verbose=0,
                   simplify=0)
