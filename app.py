import pandas as pd
from pandas.api.types import CategoricalDtype
import numpy as np
# import xlsxwriter

import dash
from dash import dcc
from dash import html
from dash.dependencies import Input, Output

import dash_bootstrap_components as dbc

import plotly.graph_objs as go

# ===================================
# Key parameters
# release_date = 'July 2023'
release_date = 'August 2023'
# ===================================
def sort_status(df):
    """
    convert column 'Status' to categorical
    https://pandas.pydata.org/pandas-docs/stable/user_guide/categorical.html
    """
    status_order = [
        'operating',
        'mothballed',
        'announced',
        'pre-permit',
        'permitted',
        'construction',
        'retired',
        'shelved',
        'cancelled',
    ]
    
    df['Status'] = df['Status'].astype(
        CategoricalDtype(status_order, ordered=False)
    )    
    df = df.sort_values(by=['Country', 'Status', 'Year'])
    
    return df

# ===================================
layout_chosen = '2 columns'  # options: '1 column', '2 columns'

# filepath = 'https://github.com/GlobalEnergyMonitor/GCPT-dashboard/blob/main/data/GCPT%20dashboard%20data%202022-07%20-%20processed%20for%20Dash%202022-08-31_1036.xlsx?raw=true'
# filepath = 'https://github.com/GlobalEnergyMonitor/GCPT-dashboard/blob/main/data/GCPT%20dashboard%20data%202023-02%20-%20processed%20for%20Dash%202023-02-13_1526.xlsx?raw=true'
filepath = 'https://github.com/GlobalEnergyMonitor/GCPT-dashboard/blob/main/data/GCPT%20dashboard%20data%202023-08%20-%20processed%20for%20Dash%202023-09-07_1623.xlsx?raw=true'

# # ===================================
dash_data_xl = pd.ExcelFile(filepath, engine='openpyxl')
gcpt_map = pd.read_excel(dash_data_xl, sheet_name='map')
gcpt_status = pd.read_excel(dash_data_xl, sheet_name='status')
gcpt_age = pd.read_excel(dash_data_xl, sheet_name='age')
gcpt_add = pd.read_excel(dash_data_xl, sheet_name='additions')

# clean status df
gcpt_status = sort_status(gcpt_status)

# create list of countries to choose from (GEM country names)
# data in gcpt_status is most complete; 
# for example, gcpt_status includes Albania, which only has cancelled units
gcpt_country_list = gcpt_status['Country'].sort_values().unique().tolist()
if gcpt_country_list[0] != 'all':
    if 'all' in gcpt_country_list:
        gcpt_country_list.remove('all')
    else:
        pass

    gcpt_country_list_for_dropdown = ['all'] + gcpt_country_list

# ===================================
# ### Create country dropdown menu

# create list of dicts needed for dropdown menu
dropdown_options_list_of_dicts = []  # initialize
for country in gcpt_country_list_for_dropdown:
    dropdown_options_list_of_dicts += [{'label': country, 'value': country}] 

# create dropdown menu
country_dropdown = dcc.Dropdown(
    id='country_dropdown',
    options=dropdown_options_list_of_dicts,
    value='all', # default starting value
    placeholder='Select a country' # only shows up if user clears entry
)

# ===================================
# ===================================
# ## Create graphs

# ===================================
# ### Choropleth map
# from https://plotly.com/python/choropleth-maps/

def create_chart_choro(gcpt_map, sel_country):    
    # Get the maximum value to cap displayed values
    min_val = int(gcpt_map['capacity log10 + 1'].min())
    max_val = int(gcpt_map['capacity log10 + 1'].max())

    # Prepare the range of the colorbar
    values = [i for i in range(min_val, max_val+2)]
    ticks = [10**i for i in values]

    # set resolution
    if sel_country == 'all':
        sel_resolution = 110
        # this drives update using fitbounds
        gcpt_map_sel = gcpt_map
        
    else:        
        # for showing individual countries, set higher resolution (smaller scale features) 
        sel_resolution = 50
        # this drives update using fitbounds
        gcpt_map_sel = gcpt_map[gcpt_map['Country'] == sel_country]
        
    # create map
    fig_map = go.Figure(
        data=go.Choropleth(
            # aspects that don't change with sel_country
            colorscale='Viridis',
            # colorbar_title = "Capacity (MW)", # don't use colorbar_title if specifying colorbar with dict, as below
            colorbar={
                'title': 'Capacity (MW)',
                'tickvals': values,
                'ticktext': ticks,
            },
            locationmode='ISO-3', # set of locations match entries in 'locations'
            zauto=False,
            zmin=min_val,
            zmax=max_val,
            
            # aspects that do change with sel_country:
            locations=gcpt_map_sel['iso_alpha'],
            z=gcpt_map_sel['capacity log10 + 1'], # data to be color-coded
            # use separate column for hover text with original capacity values
            # (data for choropleth is log scale)
            hovertemplate=gcpt_map_sel['hover_text']
    ))

    # assign title and arrange
    fig_map.update_layout(
        title_text='Operating Coal Power Capacity by Country',
        # use margin to get title placement correct
        margin={'r': 0, 't': 100, 'l': 0, 'b': 0},
        dragmode=False,
        geo=dict(
                showframe=False,
                showcoastlines=False,
                projection_type='equirectangular',
                resolution=sel_resolution,
                # fitbounds="locations", # TO DO: check if this isn't needed, because of step below
                visible=True,
            ),
    )

    # TO DO: remove line below, or fix it; it wasn't doing anything
    # fig_map.update_coloraxes(colorbar_exponentformat="power")

    # based on: https://plotly.com/python/choropleth-maps/
    # referred by: https://plotly.com/python/map-configuration/#automatic-zooming-or-bounds-fitting
    # need visible=True to show all country outlines; explained in: https://plotly.com/python/map-configuration/
    fig_map.update_geos(fitbounds="locations", visible=True)
                            
    return fig_map


def update_chart_choro(fig_map, sel_country):
    sel_locations = gcpt_map[gcpt_map['Country']==sel_country]['iso_alpha']
    fig_map.update_layout(locations=sel_locations)
    fig_map.update_geos(fitbounds="locations", visible=True)
    return fig_map


# initialize with global view
fig_map = create_chart_choro(
    gcpt_map=gcpt_map,
    sel_country='all'
)

# ===================================
# ### Total Capacity by Plant Status
# (stacked bar, vertical)

# format of color dictionary follows GreenInfo map code
gcpt_tableau_map_colors = {
  'announced': {'id': 0, 'text': 'Announced', 'color': '#76b7b2'},
  'pre-permit': {'id': 1, 'text': 'Pre-permit', 'color': '#edc948'},
  'permitted': {'id': 2, 'text': 'Permitted', 'color': '#b07aa1'},
  'construction': {'id': 3, 'text': 'Construction', 'color': '#59a14f'},
  'shelved': {'id': 4, 'text': 'Shelved', 'color': '#a9b5ae'},
  'retired': {'id': 5, 'text': 'Retired', 'color': '#f28e2b'},
  'cancelled': {'id': 6, 'text': 'Cancelled', 'color': '#767676'},
  'operating': {'id': 7, 'text': 'Operating', 'color': '#4e79a7'},
  'mothballed': {'id': 8, 'text': 'Mothballed', 'color': '#9c755f'},
}


def create_chart_by_status(gcpt_status, sel_country):
    fig_status = go.Figure() # initialize
    # select data for sel_country
    df = gcpt_status[gcpt_status['Country']==sel_country]
    statuses = df['Status'].unique().tolist()
    
    for status in statuses:
        df_status = df[df['Status']==status]
        color_status = gcpt_tableau_map_colors[status]['color']

        fig_status.add_trace(go.Bar(
            x=df_status['Year'], 
            y=df_status['Capacity (MW)'], 
            name=status, 
            marker_color=color_status,
            hovertemplate=status + ': %{y:,.0f} MW<extra></extra>' # Capacity
        ))

    fig_status.update_layout(
        barmode='stack',
        title='Coal Power Capacity by Status',
        yaxis=dict(
            title='Megawatts (MW)',
        ),
        legend=dict(
            orientation='h',
            yanchor='top',
            y=-0.1,
            xanchor='left',
            x=0,
            traceorder='normal',
        ),
    )

    return fig_status


fig_status = create_chart_by_status(
    gcpt_status=gcpt_status, 
    sel_country='all')


# ===================================
# ### Operating Coal Power by Plant Age and Type 
# By "type" it means technology

# from Data Color Picker (learnui)
age_tech_pallette = {
    'Ultra-supercritical': '#003f5c', # dark blue
    'Supercritical': '#955196', # purple
    'Subcritical': '#dd5182', # pink
    'IGCC': '#ff6e54', # orange
    'CFB': '#ffa600', # yellow
    'Unknown': '#808080' # grey
}
# not used: '#444e86', # medium blue; instead put in grey

def create_chart_age_type(gcpt_age, sel_country):
    fig_age = go.Figure() # initialize
    
    gcpt_age_sel_country = gcpt_age[gcpt_age['Country'] == sel_country].drop('Country', axis=1)
    gcpt_age_sel_country = gcpt_age_sel_country.set_index('decade')
    decades = ['0-9 years', '10-19 years', '20-29 years', '30-39 years', '40-49 years', '50+ years']
    for decade in decades:
        if decade not in gcpt_age_sel_country.index:
            new_row_df = pd.DataFrame(
                data=[[0]*len(technologies_in_order)], 
                columns=technologies_in_order, 
                index=[decade]
                )
            gcpt_age_sel_country = gcpt_age_sel_country.concat(new_row_df)

    gcpt_age_sel_country = gcpt_age_sel_country.sort_index()

    technologies_in_order = [
        'Ultra-supercritical',
        'Supercritical',
        'Subcritical',
        'IGCC',
        'CFB',
        'Unknown',
    ]

    gcpt_age_sel_country.columns.tolist()
    for technology in technologies_in_order:
        fig_age.add_trace(go.Bar(
            name=technology,
            x=gcpt_age_sel_country[technology], 
            y=gcpt_age_sel_country.index, 
            orientation='h',
            marker_color=age_tech_pallette[technology],
            hovertemplate=technology + ': %{x:,.0f} MW<extra></extra>',
        ))

    fig_age.update_layout(
        barmode='stack',
        title='Operating Coal Power Capacity by Age and Type',
        xaxis=dict(
            title='Megawatts (MW)',
        ),
        legend=dict(
            orientation='h',
            yanchor='top',
            y=-0.25,
            xanchor='left',
            x=0,
            traceorder='normal',
        ),
    )

    # reverse axis to put youngest at the top
    fig_age['layout']['yaxis']['autorange'] = "reversed"
    
    return fig_age

fig_age = create_chart_age_type(
    gcpt_age=gcpt_age, 
    sel_country='all')

# ===================================
# ### Coal Power Additions and Retirements
# * Has bars and line; see https://plotly.com/python/graphing-multiple-chart-types/

def create_chart_additions_retirements(gcpt_add, sel_country):
    fig_add = go.Figure() # initialize figure

    df = gcpt_add[gcpt_add['Country']==sel_country]
    
    df = df.rename(columns={
        'Added (MW)': 'Added', 
        'Retired (MW)': 'Retired',
        'Net added (MW)': 'Net added',
    })
    
    for status in ['Added', 'Retired']:
        df_status = df[['Year', status]].set_index('Year')

        if status == 'Retired':
            # make values negative for plotting below the horizontal axis
            df_status[status] = df_status[status] * float(-1)

        fig_add.add_trace(go.Bar(
            x=df_status.index, 
            y=df_status[status], # values are capacities (MW)
            name=status, 
            hovertemplate=status + ': %{y:,.0f} MW<extra></extra>',
        ))

    # add line for net additions
    # https://plotly.com/python/graphing-multiple-chart-types/#line-chart-and-a-bar-chart
    df_status = df[['Year', 'Net added']].set_index('Year')

    fig_add.add_trace(go.Scatter(
        x=df_status.index,
        y=df_status['Net added'],
        name='Net added',
        mode='markers',
        marker_color='black',
        hoverinfo='skip',
    ))

    # update overall layout
    fig_add.update_layout(
        barmode='relative', # instead of 'stack', to have values be negative
        title='Coal Power Capacity Added or Retired',
        yaxis=dict(
            title='Megawatts (MW)',
        ),
        legend=dict(
            orientation='h',
            yanchor='top',
            y=-0.1,
            xanchor='left',
            x=0,
        ),
    )

    return fig_add

# initialize chart with global data
fig_add = create_chart_additions_retirements(
    gcpt_add=gcpt_add,
    sel_country='all'
)

# ===================================
# Create app & server

app = dash.Dash(
    __name__, 
    external_stylesheets=[dbc.themes.BOOTSTRAP]
    )

# title based on: https://community.plotly.com/t/how-do-you-set-page-title/40115
app.title = "Coal Power dashboard"
server = app.server

# ===================================
# Create graphs of charts

dropdown_title = html.H6(children='Select a country:')
download_text = html.H6(children='Download figure data:')
download_button = html.Button("Download Excel file", id="btn_xlsx"),

choro_graph = dcc.Graph(
    id='chart_choro', 
    figure=fig_map, 
    config={'displayModeBar': False}
    )

status_graph = dcc.Graph(
    id='chart_status', 
    figure=fig_status,
    config={'displayModeBar': False}
    )

age_graph = dcc.Graph(
    id='chart_age', 
    figure=fig_age,
    config={'displayModeBar': False}
    )

add_graph = dcc.Graph(
    id='chart_add', 
    figure=fig_add,
    config={'displayModeBar': False}
    )

# ===================================
# Define layout

if layout_chosen == '1 column':
    # 1-column version
    app.layout = dbc.Container(fluid=True, children=[
        dbc.Row([dbc.Col(country_dropdown)], align='center'),
        dbc.Row([dbc.Col(choro_graph)], align='center'),
        dbc.Row([dbc.Col(status_graph)], align='center'),
        dbc.Row([dbc.Col(age_graph)], align='center'),
        dbc.Row([dbc.Col(add_graph)], align='center'),
    ],
    )
elif layout_chosen == '2 columns':
    # 2-column version
    # download based on: https://dash.plotly.com/dash-core-components/download
    app.layout = dbc.Container(fluid=True, children=[
        dbc.Row([
            dbc.Col([
                dbc.Row(dropdown_title),
                dbc.Row(country_dropdown),
            ], md=4),
            dbc.Col([], xl=5) # spacer
            # # section for download button:
            # dbc.Col([
            #     dbc.Row(download_text),
            #     dbc.Row(download_button),
            #     html.Div(id='dynamic-dropdown-container', children=[]), # EXPERIMENTAL
            #     dcc.Download(id="download-dataframe-xlsx"),
            # ], md = 2),
        ]),
        dbc.Row([
            dbc.Col(choro_graph, xl=6, align="start"),
            dbc.Col(status_graph, xl=6, align="start"),
        ]),
        dbc.Row([
            dbc.Col(age_graph, xl=6, align="start"),
            dbc.Col(add_graph, xl=6, align="start"),
        ]),
        dbc.Row([
            dbc.Col([
                html.H6(f'Data from Global Coal Plant Tracker, {release_date} release'),
            ]),
        ]),
    ],
    )

@app.callback(
    Output('chart_choro', 'figure'),
    Output('chart_status', 'figure'),
    Output('chart_age', 'figure'),
    Output('chart_add', 'figure'),
    Input('country_dropdown', 'value'), 
)
def update_figure(sel_country):
    fig_map = create_chart_choro(
        gcpt_map=gcpt_map, 
        sel_country=sel_country
    )
    fig_status = create_chart_by_status(
        gcpt_status=gcpt_status, 
        sel_country=sel_country
    )
    fig_age = create_chart_age_type(
        gcpt_age=gcpt_age,
        sel_country=sel_country
    )
    fig_add = create_chart_additions_retirements(
        gcpt_add=gcpt_add, 
        sel_country=sel_country
    )
    fig_map.update_layout(transition_duration=500)
    fig_status.update_layout(transition_duration=500)
    fig_age.update_layout(transition_duration=500)
    fig_add.update_layout(transition_duration=500)

    return fig_map, fig_status, fig_age, fig_add

# # Section for download file
# @app.callback(
#     Output("download-dataframe-xlsx", "data"), # for download button
#     Output('dynamic-dropdown-container', 'children'), # EXPERIMENTAL
#     # Output('country_dropdown', 'value'),
#     Input("btn_xlsx", "n_clicks"), # for download button
#     prevent_initial_call=True,
# )
# def func(n_clicks, children):
#     """For download button"""
#     # hardcode value for testing
#     sel_country = 'Bangladesh'

#     status_sel = gcpt_status.copy()[gcpt_status['Country']==sel_country]
#     status_sel['Status'] = status_sel['Status'].astype(str)
#     status_sel = status_sel.set_index(['Year', 'Status'])[['Capacity (MW)']]
#     status_sel = status_sel.unstack(-1)

#     # drop level for columns to remove 'Capacity (MW)'
#     status_sel = status_sel.droplevel(0, axis=1)
#     status_sel = status_sel.reset_index()
#     status_sel = status_sel.rename(columns={'Year': 'year'})

#     # TO DO: write header row that contains Country (and more)
#     table_title = f"{sel_country} - Coal Power Capacity (MW) by Status"

#     # Create a Pandas Excel writer using XlsxWriter as the engine.
#     writer = pd.ExcelWriter('Global Coal Plant Tracker dashboard export.xlsx', engine='xlsxwriter')

#     # Write each dataframe to a different worksheet.
#     status_sheet_name = 'Capacity by Status'
#     status_sel.to_excel(
#         writer, 
#         sheet_name=status_sheet_name, 
#         startrow=1, 
#         index=False
#     )
#     sheet1 = writer.sheets[status_sheet_name]
#     sheet1.write('A1', table_title)
#     # df2.to_excel(writer, sheet_name='Sheet2')
#     # df3.to_excel(writer, sheet_name='Sheet3')

#     # Close the Pandas Excel writer and output the Excel file.
#     writer.save()

#     return dcc.send_file('Global Coal Plant Tracker dashboard export.xlsx')

#     # return dcc.send_data_frame(
#     #     status_sel.to_excel, 
#     #     "GCPT_dash_export.xlsx", 
#     #     sheet_name="Capacity by Status", 
#     #     index=False,
#     # )

if __name__ == '__main__':
    app.run_server()