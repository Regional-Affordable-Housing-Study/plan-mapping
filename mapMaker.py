import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import os
import re
from IPython.display import HTML

os.chdir(r'c:\users\brenn\documents\research\rhna\planMap')

gdf = gpd.read_file(r'C:\GIS\drcog\muni_2022')
df = pd.read_excel('Consolidated Plan Scoring.xlsx')

drop_cols = ['Unnamed: {0}'.format(i) for i in range(102) if i % 2 == 1 and i != 1]
df.drop(columns = drop_cols, inplace = True)

cty = gpd.read_file(r'C:\GIS\census\tl_2021_us_county')
cty.query('STATEFP == "08"', inplace = True)
cty.to_crs(gdf.crs, inplace = True)

cty = cty[['NAME', 'geometry']].copy()

## Get County List for Each Muni
mgdf = gdf.overlay(cty, how = 'intersection')
mgdf = mgdf[['city', 'NAME', 'geometry']].copy()
mgdf['area'] = mgdf.geometry.area
area_cut = 6.129305e+05
area = 5280**2 * 2
mgdf.query('area > @area_cut', inplace = True)

cntys = mgdf.NAME.unique()

cty.query('NAME in @cntys', inplace = True)

## Add geometries for unincorporated areas
dgdf = cty.overlay(gdf, how = 'difference')
dgdf.columns = ['Municipality', 'geometry']
dgdf.Municipality = dgdf.Municipality.apply(lambda s: f'{s} County')

clist = mgdf.groupby('city').NAME.agg({lambda x: list(x)})
clist.rename(columns = {'NAME' : 'counties'}, inplace = True)

## Muni List
munis = df.columns[1:]

## Format Spatial Data
gdf = gdf[['city', 'geometry']].copy()
gdf.rename(columns = {'city' : 'Municipality'}, inplace = True)

gdf = pd.concat([gdf, dgdf])

## Format Score Data

df.dropna(subset = ['q'], inplace = True)
df.drop(columns = ['No', 'Yes'], inplace = True)

df.rename(columns = {'Town/City' : 'ques'}, inplace = True)

df.q = df.q.str.strip()
df.ques = df.ques.str.strip()

phead = np.nan
for idx, val in df.iterrows():
    if val['q'] == "Header":
        phead = val['ques']
    elif val['q'] not in ['q', 'type', 'ts', 'Header']:
        df.loc[idx, 'q'] = phead

df.query('q != "Header"', inplace = True)

# col = 'general'
# drop_idx = []
# for idx, val in df.iterrows():
#     if val[munis].isna().sum() > (len(munis) - 3):
#         col = val['q']
#         drop_idx.append(idx)
#     else:
#         df.loc[idx, 'ques'] = col
# df.drop(index = drop_idx, inplace = True)


df.set_index(['q', 'ques'], inplace = True)

ysub = re.compile(r'.*yes.*', re.IGNORECASE)
nsub = re.compile(r'.*no.*', re.IGNORECASE)

df = df.replace(ysub, 1, regex=True)
df = df.replace(nsub, 0, regex=True)

ag = df.groupby(level = 'q').sum()
tag = df.groupby(level = 'q').count().reset_index()
tag = tag[['q', 'Adams County']].copy()
tag.rename(columns = {'Adams County' : 'Total Possible'}, inplace = True)
tag.query('q not in ["ts", "type"]', inplace = True)
tag.loc[len(tag.index)] = ['Total Score', tag['Total Possible'].sum()]
tag.set_index('q', inplace = True)

agt = ag.T.reset_index(names = 'Municipality')

agt[agt.columns[1:-2]] = agt[agt.columns[1:-2]].astype(int)
agt['ts'] = agt[agt.columns[1:-2]].sum(axis = 1)
agt.type = agt.type.str.strip().fillna('Other')

agt.rename(columns = {'ts' : 'Total Score', 'type' : 'Type'}, inplace = True)


# col_0 = [x for (x, y) in dft.columns]
# col_1 = [y for (x, y) in dft.columns]
# col_0_unique = []
# for x in col_0:
#     if x not in col_0_unique:
#         col_0_unique.append(x)
#
# q_col = [(x, y) for (x, y) in zip(col_0[2:], col_1[2:])]
#
# for col in q_col:
#     dft[col] = dft[col].fillna('x').str.strip().str.lower().str[0]
#     dft[col] = dft[col].map({'y' : True, 'n' : False, 'u' : True})
#
# dft[q_col] = dft[q_col].fillna(False)
#
# new_dict = {}
# new_dict['Municipality'] = dft.index
# new_dict['County'] = dft[('general', 'County')]
# new_dict['Type'] = dft[('general', 'Type')]
# new_dict['Total Score'] = dft[q_col].sum(axis = 1)
#
# for broad in col_0_unique[1:]:
#     new_dict[broad] = dft[broad].sum(axis = 1)
#
# ndf = pd.DataFrame(new_dict)
#
# ndf.reset_index(inplace = True, drop = True)
# ndf['Municipality'] = ndf.Municipality.str.strip()
# ndf['Municipality'] = ndf.Municipality.replace('Boulder City', 'Boulder')
# ndf['Municipality'] = ndf.Municipality.replace('Lousiville', 'Louisville')
# ndf['Municipality'] = ndf.Municipality.replace('Bennet', 'Bennett')

## Join Data

fdf = gdf.merge(agt, how = 'right', on = 'Municipality')

cats = ['Total Score'] + agt.columns[1:-2].tolist()

st = """  <tr>
    <td>{0}</td>
    <td>{1} / {2}</td>
    <td>{3}</td>
    <td>{4} / {5}</td>
  </tr>"""

tab_form = '''<colgroup>
   <col span="1" style="width: 40%;">
   <col span="1" style="width: 10%;">
   <col span="1" style="width: 40%;">
   <col span="1" style="width: 10%;">
</colgroup>
'''

# max_points = {}
# max_points[cats[0]] = len(dft[cats[1:]].columns)
# for cat in cats[1:]:
#     max_points[cat] = len(dft[cat].columns)

def popinator(r):
    ret_str = '<a style="font-size:200%;color:Black">Municipality: <a style="font-size:200%;" href="munis/{0}.html">{0}</a></a><br>'.format(r.Municipality)
    ret_str += '<a style="font-size:150%;color:black" >Type: {0}</a>\n'.format(r.Type)

    ret_str += '<table>\n'
    ret_str += tab_form
    for i in range(int(len(cats)/2)):
        cat = cats[i]
        cat2 = cats[i + 7]
        ret_str += st.format(cat, r[cat], tag.loc[cat, 'Total Possible'], cat2, r[cat2], tag.loc[cat2, 'Total Possible'])
    ret_str += '\n</table>'
    return ret_str

fdf['popup'] = fdf.apply(popinator, axis = 1)

fdf = fdf.merge(clist, left_on = 'Municipality', right_on = 'city', how = 'left')
fdf.rename(columns = {"<lambda>" : 'Counties'}, inplace = True)
fdf.Counties = fdf.Counties.apply(lambda s: ','.join(s) if isinstance(s, list) else s)
fdf.Counties = fdf.apply(lambda r: r.Municipality.split(' ')[0] if pd.isna(r.Counties) else r.Counties, axis = 1)

fdf.to_crs(epsg = '4326', inplace = True)
fdf.to_file('map/plan.geojson', driver = 'GeoJSON')


def radio_maker():
    first_string = '''					<div class="row">
						<div class="column1">'''

    middle_string = '''						</div>
						<div class="column2">'''

    final_string = '''						</div>'''

    rad_string = '''		    <div>
                <input type="radio" class = "section" id={idx} name="map value" value="{cat}"
                        unchecked>
                <label for="{idx}">{cat}</label>
                </div>'''

    print(first_string)
    for i in range(len(cats)):
        if i == 7:
            print(middle_string)
        cat = cats[i]
        idx = f'cat{i}'
        print(rad_string.format(cat = cat, idx = idx))
    print(final_string)

def type_maker():
    type_string = '''							<input type="checkbox" class="type" name="type" value="{0}" checked="true">
                                <label for="{0}">{0}</label><br>'''

    for t in fdf.Type.unique():
        print(type_string.format(t))

df.rename(index = {'ts' : '', 'TOTAL SCORE' : 'Total Score', 'Type' : 'Typology', 'type' : ''}, inplace = True)
df.reset_index(inplace = True)

df.rename(columns = {'q' : 'Category', 'ques' : 'Specific'}, inplace = True)
df.set_index(['Category', 'Specific'], inplace = True)

for muni in df.columns:
    df[[muni]].to_html(f'map/munis/{muni}.html')