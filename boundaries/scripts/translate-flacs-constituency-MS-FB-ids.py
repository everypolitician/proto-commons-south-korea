import csv
import re


gu_csv = 'districts-gu.csv'
flacs_constituencies = 'flacs-constituencies.csv'
new_csv = 'translated-flacs-constituencies.csv'
flacs_csv = 'flacs_lookup.csv'
county_csv = 'county.csv'
city_csv = 'city.csv'

admin_translator = {}
flacs_lookup = {}


# make flacs code to Hangul mapping
with open(flacs_csv, newline='') as csvfile:
    reader = csv.DictReader(csvfile, delimiter=',')
    for row in reader:
        flacs_lookup[str(row['code'])] = row['Hangul']

# Make district Hangul to english Mapping
with open(gu_csv, newline='') as csvfile:
    gu_reader = csv.DictReader(csvfile, delimiter=',')
    for row in gu_reader:
        admin_translator[row['Korean']] = row['District']

# Make county Hangul to english Mapping
with open(county_csv, newline='') as csvfile:
    reader = csv.DictReader(csvfile, delimiter=',')
    for row in reader:
        admin_translator[row['Hangul']] = row['County']

# Make city Hangul to english Mapping
with open(city_csv, newline='') as csvfile:
    reader = csv.DictReader(csvfile, delimiter=',')
    for row in reader:
        admin_translator[row['Hangul']] = row['City']

# add jeju and sejong to admin_translator
admin_translator['세종특별자치시'] = 'Sejong SSG City'
admin_translator['제주특별자치도'] = 'Jeju SSG Province'

# count things
not_found_count = 0
places_count = 0

# write a new csv file with the new_id column and a new_id populating it.
with open(flacs_constituencies, newline='') as old_csv:
    with open(new_csv, 'w', newline='') as new_csv:
        csv_reader = csv.DictReader(old_csv, delimiter=',')
        fieldnames = csv_reader.fieldnames

        # useful for testing:
        # fieldnames.append('new_id')

        csv_writer = csv.DictWriter(new_csv,
                                    delimiter=',',
                                    fieldnames=fieldnames)
        csv_writer.writeheader()
        for row in csv_reader:
            places_count += 1
            old_id = row['MS_FB']
            electoral_name = old_id.split(':')[-1]
            flacs_code = row['MS_FB_PARE'].split(':')[-1]
            flacs = flacs_lookup[flacs_code]

            processed_name = electoral_name
            constit_number = ''.join(i for i in processed_name if i.isdigit())

            # get rid of '제' if it appears before a number
            if constit_number != '':
                if '제' in processed_name:
                    pattern = '제' + constit_number
                    processed_name = re.sub(pattern,
                                            constit_number,
                                            processed_name)

            # get rid of '선거구'
            if '선거구' in processed_name:
                processed_name = processed_name.replace('선거구', '')

            # if not jeju or sejong get rid of flacs
            if flacs not in ['제주특별자치도', '세종특별자치시']:
                if flacs in processed_name:
                    processed_name = processed_name.replace(flacs, '')

            name_kr = ''.join(i for i in processed_name if not i.isdigit())

            if constit_number == '':
                constit_number = '1'

            try:
                name_en = admin_translator[name_kr]
            except KeyError:
                name_en = 'not_found'

            new_constituency_name = '{} {}'.format(name_en, constit_number)
            new_id = '{}/flacs-constituency:{}'.format(row['MS_FB_PARE'],
                                                       new_constituency_name)

            # useful for testing
            # row['new_id'] = new_id

            # overwrite MS_FB Comment out for testing
            row['MS_FB'] = new_id

            csv_writer.writerow(row)

            # Missing places hunter
            if name_en == 'not_found':
                not_found_count += 1
                print(name_en)
                print('flacs:\t{}'.format(flacs))
                print('electoral name:\t{}'.format(electoral_name))
                print('processed name:\t{}\n\n'.format(processed_name))


print('{} places not found out of {}'.format(not_found_count, places_count))
