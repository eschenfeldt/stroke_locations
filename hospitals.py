'''Load, manipulate, and write hospital location files'''
import os
import pandas as pd
import download


HOSPITAL_DIR = os.path.join('data', 'hospitals')
if not os.path.isdir(HOSPITAL_DIR):
    os.makedirs(HOSPITAL_DIR)

JC_URL = ("https://www.qualitycheck.org/file.aspx?FolderName=" +
          "StrokeCertification&c=1")


def load_hospitals(hospital_file):
    '''
    Read in the given relative filepath as a table of hospital information
    '''
    return pd.read_csv(hospital_file, sep='|').set_index('CenterID')


def master_list(update=False):
    '''
    Get the dataframe of all known hospitals, building it from Joint
        Commission certification if it doesn't exist, and optionally updating
        it to capture additions to the JC list.
    '''
    master_loc = os.path.join(HOSPITAL_DIR, 'all.csv')
    try:
        existing = load_hospitals(master_loc)
    except FileNotFoundError:
        columns = [
            'CenterID', 'CenterType',
            'OrganizationName', 'City', 'State', 'PostalCode',
            'Name', 'Address', 'Latitude', 'Longitude',
            'destination', 'destinationID', 'transfer_time',
            'DTN_1st', 'DTN_Median', 'DTN_3rd',
            'DTP_1st', 'DTP_Median', 'DTP_3rd'
        ]
        existing = pd.DataFrame(columns=columns).set_index('CenterID')

    if update or existing.empty:
        jc_file = download.download_file(JC_URL, 'Joint Commission')
        jc_data = pd.read_excel(jc_file)

        program_map = {
            'Advanced Comprehensive Stroke Center    ': 'Comprehensive',
            'Advanced Primary Stroke Center          ': 'Primary',
            # Treatment of TSCs is undecided; taking conservative approach
            'Advanced Thrombectomy Capable Stroke Ctr': 'Primary',
        }
        jc_data['CenterType'] = jc_data.CertificationProgram.map(program_map)
        jc_data = jc_data.dropna()

        # For multiple certifications, keep the comprehensive line
        #   NOTE - This ignores effective dates under the assumption that all
        #           listed certifications are active
        jc_data = jc_data.sort_values('CenterType')

        jc_data = jc_data.drop_duplicates(subset=['OrganizationId', 'City',
                                                  'State', 'PostalCode'])

        update_index = ['OrganizationName', 'City', 'State', 'PostalCode']
        jc_data = jc_data.set_index(update_index, verify_integrity=True)

        existing = existing.reset_index().set_index(update_index)

        new = jc_data[~jc_data.index.isin(existing.index)]
        out = pd.concat([existing, new], sort=False)
        out.update(jc_data)
        out = out.reset_index()

        next_ID = out.CenterID.max() + 1
        if pd.isnull(next_ID):
            next_ID = 1
        for i in out.index:
            if pd.isnull(out.CenterID[i]):
                out.loc[i, 'CenterID'] = next_ID
                next_ID += 1

        out.CenterID = out.CenterID.astype(int)
        out = out.set_index('CenterID', verify_integrity=True)
        out.to_csv(master_loc, sep='|')
    else:
        out = existing

    return out