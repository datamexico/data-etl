
def format_text(df, cols_names=None, stopwords=None):
    # format
    for ele in cols_names:
        df[ele] = df[ele].str.title().str.strip()
        for ene in stopwords:
            df[ele] = df[ele].str.replace(' ' + ene.title() + ' ', ' ' + ene + ' ')

    return df

def representative_values(df, target_col, target_val, target_threshold=10):
    count = df.shape[0]
    value = len(list(df.loc[df[target_col] == target_val, target_col]))
    #print(count, value, 'temp')
    result = round((value/count)*100, 3)
    if result > target_threshold:
        return [target_col, target_threshold, result, False]
    else:
        return [target_col, target_threshold, result, True]

def validate_category(df, dim_column, target_column, target_value, threshold=0.1):
    """dim_column: 'sector_id'
       target_column: 'value_c'
       target_value: 'c'
    """
    temp = df.copy()
    for sector in list(df[dim_column].unique()):
        temp[target_column] = temp[target_column].astype(str).str.lower()
        count = temp.loc[temp[dim_column] == sector, target_column].shape[0]
        value = len(list(temp.loc[(temp[dim_column] == sector) & (temp[target_column] == target_value), target_column]))
        restul = round((value/count)*100, 3)
        if restul > 10:
            #print('result: {}%, drop: {}, ID: {}'.format(restul, True, sector))
            temp = temp.loc[temp[dim_column] != sector].copy()
        else:
            #print('result: {}%, drop: {}, ID: {}'.format(restul, False, sector))
            pass
    
    #print('init: {}, end: {}'.format(df.shape[0], temp.shape[0]))
    return temp