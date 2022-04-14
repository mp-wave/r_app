import matplotlib.pyplot as plt
import pandas as pd

import os
from natsort import natsorted
import streamlit as st
import pandas as pd
from scipy.stats import zscore
from streamlit.legacy_caching.hashing import _CodeHasher
import seaborn as sns
import matplotlib.font_manager as fm
import numpy as np
from streamlit.server.server import Server
from io import BytesIO
import xlsxwriter
#from streamlit.script_run_context import get_script_run_ctx


fontPathBold = "./PTSans-Bold.ttf"
fontPathNBold = "./PTSans-Regular.ttf"
titles = fm.FontProperties(fname=fontPathBold, size=32)
subtitles = fm.FontProperties(fname=fontPathNBold, size=20)
labels = fm.FontProperties(fname=fontPathNBold, size=12)


@st.cache(allow_output_mutation=True)
def load_data():
    #url = 'https://drive.google.com/file/d/1KD5nxMlZZImiArxLXg4N43uiUkJ4taQP/view?usp=sharing'
    #path = 'https://drive.google.com/uc?export=download&id='+url.split('/')[-2]
    path = './Wyscout_All_Leagues_Data.csv'
    df = pd.read_csv(path)
    df.Team = df['Team within selected timeframe']
    #df = df[(df.Team.isin(player)) & (df.Season.isin(season))]
    return df

def main():
    state = _get_state()
    pages = {
        "Player Comparison Charts": Percentile,
        "Positional Formatted Dataframes": positional_zscore_df
    }

    # st.sidebar.title("Page Filters")
    page = st.sidebar.radio("Select Page", tuple(pages.keys()))

    # Display the selected page with the session state
    pages[page](state)

    # Mandatory to avoid rollbacks with widgets, must be called at the end of your app
    state.sync()


def display_state_values(state):
    st.write("Input state:", state.input)
    st.write("Slider state:", state.slider)
    # st.write("Radio state:", state.radio)
    st.write("Checkbox state:", state.checkbox)
    st.write("Selectbox state:", state.selectbox)
    st.write("Multiselect state:", state.multiselect)

    for i in range(3):
        st.write(f"Value {i}:", state[f"State value {i}"])

    if st.button("Clear state"):
        state.clear()


def multiselect(label, options, default, format_func=str):
    """multiselect extension that enables default to be a subset list of the list of objects
     - not a list of strings

     Assumes that options have unique format_func representations

     cf. https://github.com/streamlit/streamlit/issues/352
     """
    options_ = {format_func(option): option for option in options}
    default_ = [format_func(option) for option in default]
    selections = st.multiselect(
        label, options=list(options_.keys()), default=default_, format_func=format_func
    )
    return [options_[format_func(selection)] for selection in selections]


# selections = multiselect("Select", options=[Option1, Option2], default=[Option2])


class _SessionState:

    def __init__(self, session, hash_funcs):
        """Initialize SessionState instance."""
        self.__dict__["_state"] = {
            "data": {},
            "hash": None,
            "hasher": _CodeHasher(hash_funcs),
            "is_rerun": False,
            "session": session,
        }

    def __call__(self, **kwargs):
        """Initialize state data once."""
        for item, value in kwargs.items():
            if item not in self._state["data"]:
                self._state["data"][item] = value

    def __getitem__(self, item):
        """Return a saved state value, None if item is undefined."""
        return self._state["data"].get(item, None)

    def __getattr__(self, item):
        """Return a saved state value, None if item is undefined."""
        return self._state["data"].get(item, None)

    def __setitem__(self, item, value):
        """Set state value."""
        self._state["data"][item] = value

    def __setattr__(self, item, value):
        """Set state value."""
        self._state["data"][item] = value

    def clear(self):
        """Clear session state and request a rerun."""
        self._state["data"].clear()
        self._state["session"].request_rerun()

    def sync(self):
        """Rerun the app with all state values up to date from the beginning to fix rollbacks."""

        # Ensure to rerun only once to avoid infinite loops
        # caused by a constantly changing state value at each run.
        #
        # Example: state.value += 1
        if self._state["is_rerun"]:
            self._state["is_rerun"] = False

        elif self._state["hash"] is not None:
            if self._state["hash"] != self._state["hasher"].to_bytes(self._state["data"], None):
                self._state["is_rerun"] = True
                self._state["session"].request_rerun()

        self._state["hash"] = self._state["hasher"].to_bytes(self._state["data"], None)


def _get_session():
    session_id = st._get_script_run_ctx().session_id
    session_info = Server.get_current()._get_session_info(session_id)

    if session_info is None:
        raise RuntimeError("Couldn't get your Streamlit Session object.")

    return session_info.session


def _get_state(hash_funcs=None):
    session = _get_session()

    if not hasattr(session, "_custom_session_state"):
        session._custom_session_state = _SessionState(session, hash_funcs)

    return session._custom_session_state

def positional_zscore_df(state):
    df = load_data()

    col1, col2= st.columns(2)
    with col1:
        league = st.selectbox('Select League', natsorted(df.country_league.unique()))
    league_df = df[df['country_league'] == league]
    with col2:
        position = st.selectbox('Select Position', ['CF', 'W', 'AM-CM', 'DM', 'FB', 'CB'])

    st.markdown('## Conditional Formatted Dataframe')
    st.text('Sortable Table - Colored by ZScore by Positional Group within League - Use Download Button to View Easiest in Excel with Panes Frozen')
    st.markdown('#')

    if position == 'CF':
        position_df = league_df[league_df['Position'].str.contains(position, na=False)]
        filter_df = position_df[(position_df['Minutes played'] >= 350) & (position_df.Team.notnull())]
        player_data = pd.DataFrame(filter_df,
                                   columns=['Team', 'Player', 'Age', 'Minutes played',  'Non-penalty goals per 90', 'xG per 90',
                                            'Shots per 90', 'Shots on target, %', 'Goal conversion, %', 'Touches in box per 90',
                                            'Passes per 90', 'Accurate passes, %', 'Passes to penalty area per 90', 'Accurate passes to penalty area, %',
                                            'Dribbles per 90', 'Successful defensive actions per 90', 'Aerial duels won, %', 'PAdj Interceptions',
                                            ]).reset_index()
        col_list = [ 'Non-penalty goals per 90', 'xG per 90', 'Shots per 90', 'Shots on target, %',  'Goal conversion, %',
                     'Touches in box per 90', 'Passes per 90', 'Accurate passes, %', 'Passes to penalty area per 90', 'Accurate passes to penalty area, %',
                     'Dribbles per 90', 'Successful defensive actions per 90', 'Aerial duels won, %', 'PAdj Interceptions']
        player_data = player_data.fillna(0)
        player_data.Age = player_data.Age.astype(int)
        player_df = player_data

        player_data[col_list] = player_data[col_list].apply(zscore)
        player_data = player_data.drop(columns=['index'])
        hide_dataframe_row_index = """
                                <style>
                                .row_heading.level0 {display:none}
                                .blank {display:none}
                                </style>
                        """
        st.markdown(hide_dataframe_row_index, unsafe_allow_html=True)

        cf_df = (player_data.style.background_gradient(vmin=-3, vmax=3,
                                               cmap=sns.color_palette("seismic_r", as_cmap=True),
                                               subset=col_list))


        st.dataframe(cf_df, width=1280, height=768)

        fn = str(position)+' - '+str(league)+' DataFrame.xlsx'

        def to_excel(df):
            output = BytesIO()
            writer = pd.ExcelWriter(output, engine='xlsxwriter')
            df.to_excel(writer, index=False, sheet_name='Sheet1')
            workbook = writer.book
            worksheet = writer.sheets['Sheet1']
            format1 = workbook.add_format({'num_format': '0.00'})
            worksheet.set_column('A:A', None, format1)
            worksheet.freeze_panes('C2')
            writer.save()
            processed_data = output.getvalue()
            return processed_data

        df_xlsx = to_excel(cf_df)
        st.download_button(label='Download Data as XLSX',
                           data=df_xlsx,
                           file_name=fn)


    elif position == 'W':
        position_df = league_df[(league_df['Position'].str.contains('WF', na=False))|(league_df['Position'].str.contains('RW', na=False))|(league_df['Position'].str.contains('LW', na=False))]
        filter_df = position_df[(position_df['Minutes played'] >= 350) & (position_df.Team.notnull())]
        player_data = pd.DataFrame(filter_df,
                                   columns=['Team', 'Player', 'Age', 'Minutes played',  'Non-penalty goals per 90', 'xG per 90',
                                            'Shots per 90', 'Touches in box per 90', 'xA per 90', 'Shot assists per 90', 'Passes to penalty area per 90', 'Accurate passes to penalty area, %',
                                            'Passes per 90', 'Accurate passes, %', 'Progressive passes per 90','Dribbles per 90', 'Progressive runs per 90',
                                            'Successful defensive actions per 90',  'PAdj Interceptions'
                                            ]).reset_index()
        col_list = ['Non-penalty goals per 90', 'xG per 90','Shots per 90', 'Touches in box per 90', 'xA per 90', 'Shot assists per 90',
                    'Passes to penalty area per 90', 'Accurate passes to penalty area, %','Passes per 90', 'Accurate passes, %', 'Progressive passes per 90',
                    'Dribbles per 90', 'Progressive runs per 90','Successful defensive actions per 90', 'PAdj Interceptions']
        player_data = player_data.fillna(0)
        player_data.Age = player_data.Age.astype(int)
        player_df = player_data

        player_data[col_list] = player_data[col_list].apply(zscore)
        player_data = player_data.drop(columns=['index'])
        hide_dataframe_row_index = """
                                <style>
                                .row_heading.level0 {display:none}
                                .blank {display:none}
                                </style>
                        """
        st.markdown(hide_dataframe_row_index, unsafe_allow_html=True)

        cf_df = (player_data.style.background_gradient(vmin=-3, vmax=3,
                                               cmap=sns.color_palette("seismic_r", as_cmap=True),
                                               subset=col_list))


        st.dataframe(cf_df, width=1280, height=768)

        fn = str(position)+' - '+str(league)+' DataFrame.xlsx'

        def to_excel(df):
            output = BytesIO()
            writer = pd.ExcelWriter(output, engine='xlsxwriter')
            df.to_excel(writer, index=False, sheet_name='Sheet1')
            workbook = writer.book
            worksheet = writer.sheets['Sheet1']
            format1 = workbook.add_format({'num_format': '0.00'})
            worksheet.set_column('A:A', None, format1)
            worksheet.freeze_panes('C2')
            writer.save()
            processed_data = output.getvalue()
            return processed_data

        df_xlsx = to_excel(cf_df)
        st.download_button(label='Download Data as XLSX',
                           data=df_xlsx,
                           file_name=fn)


    elif position == 'AM-CM':
        position_df = league_df[(league_df['Position'].str.contains('AM', na=False))|(league_df['Position'].str.contains('CM', na=False))]
        filter_df = position_df[(position_df['Minutes played'] >= 350) & (position_df.Team.notnull())]
        player_data = pd.DataFrame(filter_df,
                                   columns=['Team', 'Player', 'Age', 'Minutes played', 'Non-penalty goals per 90',
                                            'xG per 90', 'Touches in box per 90', 'xA per 90', 'Assists per 90', 'Shot assists per 90', 'Second assists per 90',
                                            'Passes per 90', 'Accurate passes, %', 'Forward passes per 90', 'Accurate forward passes, %',
                                            'Passes to final third per 90', 'Progressive passes per 90', 'Passes to penalty area per 90',
                                            'Dribbles per 90', 'Progressive runs per 90',
                                            'Successful defensive actions per 90', 'PAdj Interceptions'
                                            ]).reset_index()
        col_list = ['Non-penalty goals per 90',
                                            'xG per 90', 'Touches in box per 90', 'xA per 90', 'Assists per 90', 'Shot assists per 90', 'Second assists per 90',
                                            'Passes per 90', 'Accurate passes, %', 'Forward passes per 90', 'Accurate forward passes, %',
                                            'Passes to final third per 90', 'Progressive passes per 90', 'Passes to penalty area per 90',
                                            'Dribbles per 90', 'Progressive runs per 90',
                                            'Successful defensive actions per 90', 'PAdj Interceptions']
        player_data = player_data.fillna(0)
        player_data.Age = player_data.Age.astype(int)
        player_df = player_data
        player_data[col_list] = player_data[col_list].apply(zscore)
        player_data = player_data.drop(columns=['index'])
        hide_dataframe_row_index = """
                                <style>
                                .row_heading.level0 {display:none}
                                .blank {display:none}
                                </style>
                        """
        st.markdown(hide_dataframe_row_index, unsafe_allow_html=True)

        cf_df = (player_data.style.background_gradient(vmin=-3, vmax=3,
                                               cmap=sns.color_palette("seismic_r", as_cmap=True),
                                               subset=col_list))


        st.dataframe(cf_df, width=1280, height=768)

        fn = str(position)+' - '+str(league)+' DataFrame.xlsx'

        def to_excel(df):
            output = BytesIO()
            writer = pd.ExcelWriter(output, engine='xlsxwriter')
            df.to_excel(writer, index=False, sheet_name='Sheet1')
            workbook = writer.book
            worksheet = writer.sheets['Sheet1']
            format1 = workbook.add_format({'num_format': '0.00'})
            worksheet.set_column('A:A', None, format1)
            worksheet.freeze_panes('C2')
            writer.save()
            processed_data = output.getvalue()
            return processed_data

        df_xlsx = to_excel(cf_df)
        st.download_button(label='Download Data as XLSX',
                           data=df_xlsx,
                           file_name=fn)

    elif position == 'DM':
        position_df = league_df[(league_df['Position'].str.contains(position, na=False))]
        filter_df = position_df[(position_df['Minutes played'] >= 350) & (position_df.Team.notnull())]
        player_data = pd.DataFrame(filter_df,
                                   columns=['Team', 'Player', 'Age', 'Minutes played', 'Passes per 90', 'Accurate passes, %',
                                            'Forward passes per 90', 'Accurate forward passes, %',  'Passes to final third per 90', 'Accurate passes to final third, %',
                                            'Passes to penalty area per 90', 'Progressive passes per 90', 'Through passes per 90','Dribbles per 90',
                                            'Progressive runs per 90', 'Successful defensive actions per 90', 'Defensive duels won, %',
                                            'Aerial duels per 90', 'Aerial duels won, %', 'PAdj Interceptions'
                                            ]).reset_index()
        col_list = [ 'Passes per 90', 'Accurate passes, %',
                                            'Forward passes per 90', 'Accurate forward passes, %',  'Passes to final third per 90', 'Accurate passes to final third, %',
                                            'Passes to penalty area per 90', 'Progressive passes per 90', 'Through passes per 90','Dribbles per 90',
                                            'Progressive runs per 90', 'Successful defensive actions per 90', 'Defensive duels won, %',
                                            'Aerial duels per 90', 'Aerial duels won, %', 'PAdj Interceptions']
        player_data = player_data.fillna(0)
        player_data.Age = player_data.Age.astype(int)
        player_df = player_data
        player_data[col_list] = player_data[col_list].apply(zscore)
        player_data = player_data.drop(columns=['index'])
        hide_dataframe_row_index = """
                                <style>
                                .row_heading.level0 {display:none}
                                .blank {display:none}
                                </style>
                        """
        st.markdown(hide_dataframe_row_index, unsafe_allow_html=True)

        cf_df = (player_data.style.background_gradient(vmin=-3, vmax=3,
                                               cmap=sns.color_palette("seismic_r", as_cmap=True),
                                               subset=col_list))


        st.dataframe(cf_df, width=1280, height=768)

        fn = str(position)+' - '+str(league)+' DataFrame.xlsx'

        def to_excel(df):
            output = BytesIO()
            writer = pd.ExcelWriter(output, engine='xlsxwriter')
            df.to_excel(writer, index=False, sheet_name='Sheet1')
            workbook = writer.book
            worksheet = writer.sheets['Sheet1']
            format1 = workbook.add_format({'num_format': '0.00'})
            worksheet.set_column('A:A', None, format1)
            worksheet.freeze_panes('C2')
            writer.save()
            processed_data = output.getvalue()
            return processed_data

        df_xlsx = to_excel(cf_df)
        st.download_button(label='Download Data as XLSX',
                           data=df_xlsx,
                           file_name=fn)
    elif position == 'FB':
        position_df = league_df[(league_df['Position'].str.contains('LB', na=False))|(league_df['Position'].str.contains('RB', na=False))]
        filter_df = position_df[(position_df['Minutes played'] >= 350) & (position_df.Team.notnull())]
        player_data = pd.DataFrame(filter_df,
                                   columns=['Team', 'Player', 'Age', 'Minutes played', 'Passes per 90', 'Accurate passes, %',
                                            'Forward passes per 90', 'Accurate forward passes, %',  'Passes to final third per 90', 'Accurate passes to final third, %',
                                            'Passes to penalty area per 90', 'Accurate passes to penalty area, %', 'Progressive passes per 90', 'Dribbles per 90',
                                            'Progressive runs per 90', 'Successful defensive actions per 90', 'Defensive duels won, %',
                                            'Aerial duels per 90', 'Aerial duels won, %', 'PAdj Interceptions'
                                            ]).reset_index()
        col_list = ['Passes per 90', 'Accurate passes, %',
                                            'Forward passes per 90', 'Accurate forward passes, %',  'Passes to final third per 90', 'Accurate passes to final third, %',
                                            'Passes to penalty area per 90', 'Accurate passes to penalty area, %', 'Progressive passes per 90', 'Dribbles per 90',
                                            'Progressive runs per 90', 'Successful defensive actions per 90', 'Defensive duels won, %',
                                            'Aerial duels per 90', 'Aerial duels won, %', 'PAdj Interceptions']
        player_data = player_data.fillna(0)
        player_data.Age = player_data.Age.astype(int)
        player_df = player_data
        player_data[col_list] = player_data[col_list].apply(zscore)
        player_data = player_data.drop(columns=['index'])
        hide_dataframe_row_index = """
                                <style>
                                .row_heading.level0 {display:none}
                                .blank {display:none}
                                </style>
                        """
        st.markdown(hide_dataframe_row_index, unsafe_allow_html=True)

        cf_df = (player_data.style.background_gradient(vmin=-3, vmax=3,
                                               cmap=sns.color_palette("seismic_r", as_cmap=True),
                                               subset=col_list))


        st.dataframe(cf_df, width=1280, height=768)

        fn = str(position)+' - '+str(league)+' DataFrame.xlsx'

        def to_excel(df):
            output = BytesIO()
            writer = pd.ExcelWriter(output, engine='xlsxwriter')
            df.to_excel(writer, index=False, sheet_name='Sheet1')
            workbook = writer.book
            worksheet = writer.sheets['Sheet1']
            format1 = workbook.add_format({'num_format': '0.00'})
            worksheet.set_column('A:A', None, format1)
            worksheet.freeze_panes('C2')
            writer.save()
            processed_data = output.getvalue()
            return processed_data

        df_xlsx = to_excel(cf_df)
        st.download_button(label='Download Data as XLSX',
                           data=df_xlsx,
                           file_name=fn)

    else:
        position_df = league_df[(league_df['Position'].str.contains('CB', na=False))]
        filter_df = position_df[(position_df['Minutes played'] >= 350) & (position_df.Team.notnull())]
        player_data = pd.DataFrame(filter_df,
                                   columns=['Team', 'Player', 'Age', 'Minutes played', 'Passes per 90', 'Accurate passes, %',
                                            'Forward passes per 90', 'Accurate forward passes, %',  'Progressive passes per 90',
                                            'Long passes per 90', 'Duels per 90', 'Duels won, %', 'Dribbles per 90',
                                            'Successful defensive actions per 90', 'Defensive duels won, %',
                                            'Aerial duels per 90', 'Aerial duels won, %', 'PAdj Interceptions', 'Shots blocked per 90'
                                            ]).reset_index()
        col_list = ['Passes per 90', 'Accurate passes, %',
                                            'Forward passes per 90', 'Accurate forward passes, %',  'Progressive passes per 90',
                                            'Long passes per 90', 'Duels per 90', 'Duels won, %', 'Dribbles per 90',
                                            'Successful defensive actions per 90', 'Defensive duels won, %',
                                            'Aerial duels per 90', 'Aerial duels won, %', 'PAdj Interceptions', 'Shots blocked per 90']

        player_data = player_data.fillna(0)
        player_data.Age = player_data.Age.astype(int)
        player_df = player_data
        player_data[col_list] = player_data[col_list].apply(zscore)
        player_data = player_data.drop(columns=['index'])
        hide_dataframe_row_index = """
                                        <style>
                                        .row_heading.level0 {display:none}
                                        .blank {display:none}
                                        </style>
                                """
        st.markdown(hide_dataframe_row_index, unsafe_allow_html=True)

        cf_df = (player_data.style.background_gradient(vmin=-3, vmax=3,
                                                       cmap=sns.color_palette("seismic_r", as_cmap=True),
                                                       subset=col_list))

        st.dataframe(cf_df, width=1280, height=768)

        fn = str(position) + ' - ' + str(league) + ' DataFrame.xlsx'

        def to_excel(df):
            output = BytesIO()
            writer = pd.ExcelWriter(output, engine='xlsxwriter')
            df.to_excel(writer, index=False, sheet_name='Sheet1')
            workbook = writer.book
            worksheet = writer.sheets['Sheet1']
            format1 = workbook.add_format({'num_format': '0.00'})
            worksheet.set_column('A:A', None, format1)
            worksheet.freeze_panes('C2')
            writer.save()
            processed_data = output.getvalue()
            return processed_data

        df_xlsx = to_excel(cf_df)
        st.download_button(label='Download Data as XLSX',
                           data=df_xlsx,
                           file_name=fn)

def Percentile(state):
    df = load_data()

    col1, col2, col3 = st.columns(3)
    with col1:
        league = st.selectbox('Select League', natsorted(df.country_league.unique()))
    league_df = df[df['country_league'] == league]
    with col2:
        position = st.selectbox('Select Position', ['CF', 'W', 'AM-CM', 'DM', 'FB', 'CB'])
    if position == 'CF':
        position_df = league_df[league_df['Position'].str.contains(position, na=False)]
        filter_df = position_df[(position_df['Minutes played'] >= 350) & (position_df.Team.notnull())]
        player_data = pd.DataFrame(filter_df,
                                   columns=['Team', 'Player', 'Age', 'Minutes played',  'Non-penalty goals per 90', 'xG per 90',
                                            'Shots per 90', 'Shots on target, %', 'Goal conversion, %', 'Touches in box per 90',
                                            'Passes per 90', 'Accurate passes, %', 'Passes to penalty area per 90', 'Accurate passes to penalty area, %',
                                            'Dribbles per 90', 'Successful defensive actions per 90', 'Aerial duels won, %', 'PAdj Interceptions',
                                            ]).reset_index()
        col_list = [ 'Non-penalty goals per 90', 'xG per 90', 'Shots per 90', 'Shots on target, %',  'Goal conversion, %',
                     'Touches in box per 90', 'Passes per 90', 'Accurate passes, %', 'Passes to penalty area per 90', 'Accurate passes to penalty area, %',
                     'Dribbles per 90', 'Successful defensive actions per 90', 'Aerial duels won, %', 'PAdj Interceptions']
        player_df = player_data
        player_data = player_data.fillna(0)

        player_data[col_list] = player_data[col_list].apply(zscore)
        #player_data = player_data.rename(columns={"xG per 90":"xG/90", "Non-penalty goals per 90":"Non-pen Goals/90",
         #                                         "Shots per 90":"Shots/90", "Touches in box per 90":"TouchesinBox/90",
          #                                        "Passes per 90":"Passes/90", "Accurate passes, %":"Pass%",
           #                                       "Passes to penalty area per 90":"PassesInto18/90",
            #                                      "Accurate passes to penalty area, %":"PassesInto18%", "Dribbles per 90":"Dribbles/90",
             #                                     "Progressive runs per 90":"ProgressiveRuns/90", "Aerial duels won, %":"Aerial%"})

        #st.dataframe(player_data)
        with col3:
            player = st.selectbox('Select Player', natsorted(player_data.Player.unique()))
        player_df = player_df[player_df['Player'] == (player)]
        player_df = player_df.drop(columns=['index'])
        team = player_df.Team.unique()
        team = (','.join(team))
        # player_data = player_data.apply(zscore)
        #player_data = player_data[player_data.Player == player]
        player_data = player_data.drop(columns=['index', 'Team', 'Age', 'Minutes played'])
        player_data = player_data.set_index('Player')
        test = player_data.transpose()
        my_range = range(0, len(test.index))
        fig, ax = plt.subplots(figsize=(22, 12), facecolor='#e6e6e6')
        markers, stemlines, baseline = plt.stem(test[player],
                                                bottom=0, use_line_collection=True, markerfmt=' ')
        # markerline.set_markerfacecolor('none')
        # plt.setp(baseline, visible=False)
        # my_color = np.where(test[player]>=0, 'darkblue', 'darkred')
        my_color = np.where((test[player] >= 2), 'darkblue',  # when... then
                            np.where((test[player] >= 1), 'dodgerblue',  # when... then
                                     np.where((test[player] >= 0), 'lightblue',  # when... then
                                              np.where((test[player] <= -2), 'darkred',  # when... then
                                                       np.where((test[player] <= -1), 'red',  # when... then
                                                                np.where((test[player] <= 0), 'coral',  # when... then
                                                                         'maroon'))))))
        plt.setp(stemlines, color=my_color, lw=30)
        # plt.setp(markers, color)
        plt.scatter(test.index, test[player], marker='o', s=1250, c=my_color, edgecolors='white', lw=4, zorder=12)
        plt.setp(baseline, linestyle="-", color="black", linewidth=10)
        baseline.set_xdata([0, 1])
        baseline.set_transform(plt.gca().get_yaxis_transform())

        #ax.annotate('test', xy=(.35,3.8), zorder=25)
        ax.tick_params(axis='x', direction='out', color='black', labelsize=12)
        ax.tick_params(axis='y', direction='out', color='black', labelsize=10)
        ax.grid(color='white', linestyle='solid', linewidth=2, alpha=.5)
        ax.set_facecolor('#595959')
        player_df['Age'] = int(player_df.Age)
        #plt.title(str(player)+' - '+str(position)+'\nMinutes Played: '+str(sum(player_df['Minutes played']))+'\nAge: '+str(sum(player_df['Age'])),
         #         fontproperties=titles)
        #plt.title(str(player) + ' - ' + str(position) + '\n' + '\n', fontproperties=titles)
        fig.text(.5, .935, str(player) + ' - ' + str(team) + ' - ' + str(position) + '\n' + '\n', fontproperties=titles,
                 horizontalalignment='center', verticalalignment='center')
        fig.text(.5, .935, 'Minutes Played: '+str(sum(player_df['Minutes played'])), color='black', fontproperties=subtitles,
                 horizontalalignment='center', verticalalignment='center')
        fig.text(.5, .9, 'Age: '+str(sum(player_df['Age'])), color='black', fontproperties=subtitles,
                 horizontalalignment='center', verticalalignment='center')
        plt.ylabel('Z Score', fontproperties=labels)
        plt.yticks(fontproperties=labels)
        plt.xticks(my_range, test.index, fontproperties=labels)
        plt.xticks(rotation=25)
        plt.ylim(-3.75, 3.75)
        fig.text(.1, 0, 'Metrics Standardized by Position within League | '+str(league), color='black', fontproperties=labels)
        st.pyplot(fig)
        fn = str(player)+' - '+str(position)+' - '+str(league)+'.png'
        plt.savefig(fn, format='png', bbox_inches='tight')
        with open(fn, "rb") as file:
            btn = st.download_button(
                label="Download "+str(player)+"'s Graph",
                data=file,
                file_name=fn,
                mime="image/png"
            )
            hide_dataframe_row_index = """
                            <style>
                            .row_heading.level0 {display:none}
                            .blank {display:none}
                            </style>
                    """
        st.markdown(hide_dataframe_row_index, unsafe_allow_html=True)
        st.table(player_df)
        def convert_df(df):
            # IMPORTANT: Cache the conversion to prevent computation on every rerun
            return df.to_csv().encode('utf-8')

        #csv = convert_df(player_df)
        #st.download_button(label="Download data as CSV",data=csv,file_name='large_df.csv',mime='text/csv')
    elif position == 'W':
        position_df = league_df[(league_df['Position'].str.contains('WF', na=False))|(league_df['Position'].str.contains('RW', na=False))|(league_df['Position'].str.contains('LW', na=False))]
        filter_df = position_df[(position_df['Minutes played'] >= 350) & (position_df.Team.notnull())]
        player_data = pd.DataFrame(filter_df,
                                   columns=['Team', 'Player', 'Age', 'Minutes played',  'Non-penalty goals per 90', 'xG per 90',
                                            'Shots per 90', 'Touches in box per 90', 'xA per 90', 'Shot assists per 90', 'Passes to penalty area per 90', 'Accurate passes to penalty area, %',
                                            'Passes per 90', 'Accurate passes, %', 'Progressive passes per 90','Dribbles per 90', 'Progressive runs per 90',
                                            'Successful defensive actions per 90',  'PAdj Interceptions'
                                            ]).reset_index()
        col_list = ['Non-penalty goals per 90', 'xG per 90','Shots per 90', 'Touches in box per 90', 'xA per 90', 'Shot assists per 90',
                    'Passes to penalty area per 90', 'Accurate passes to penalty area, %','Passes per 90', 'Accurate passes, %', 'Progressive passes per 90',
                    'Dribbles per 90', 'Progressive runs per 90','Successful defensive actions per 90', 'PAdj Interceptions']
        player_df = player_data
        player_data = player_data.fillna(0)

        player_data[col_list] = player_data[col_list].apply(zscore)
        # player_data = player_data.rename(columns={"xG per 90":"xG/90", "Non-penalty goals per 90":"Non-pen Goals/90",
        #                                         "Shots per 90":"Shots/90", "Touches in box per 90":"TouchesinBox/90",
        #                                        "Passes per 90":"Passes/90", "Accurate passes, %":"Pass%",
        #                                       "Passes to penalty area per 90":"PassesInto18/90",
        #                                      "Accurate passes to penalty area, %":"PassesInto18%", "Dribbles per 90":"Dribbles/90",
        #                                     "Progressive runs per 90":"ProgressiveRuns/90", "Aerial duels won, %":"Aerial%"})

        # st.dataframe(player_data)
        with col3:
            player = st.selectbox('Select Player', natsorted(player_data.Player.unique()))
        player_df = player_df[player_df['Player'] == (player)]
        player_df = player_df.drop(columns=['index'])
        team = player_df.Team.unique()
        team = (','.join(team))
        # player_data = player_data.apply(zscore)
        # player_data = player_data[player_data.Player == player]
        player_data = player_data.drop(columns=['index', 'Team', 'Age', 'Minutes played'])
        player_data = player_data.set_index('Player')
        test = player_data.transpose()
        my_range = range(0, len(test.index))
        fig, ax = plt.subplots(figsize=(22, 12), facecolor='#e6e6e6')
        markers, stemlines, baseline = plt.stem(test[player],
                                                bottom=0, use_line_collection=True, markerfmt=' ')
        # markerline.set_markerfacecolor('none')
        # plt.setp(baseline, visible=False)
        # my_color = np.where(test[player]>=0, 'darkblue', 'darkred')
        my_color = np.where((test[player] >= 2), 'darkblue',  # when... then
                            np.where((test[player] >= 1), 'dodgerblue',  # when... then
                                     np.where((test[player] >= 0), 'lightblue',  # when... then
                                              np.where((test[player] <= -2), 'darkred',  # when... then
                                                       np.where((test[player] <= -1), 'red',  # when... then
                                                                np.where((test[player] <= 0), 'coral',
                                                                         # when... then
                                                                         'maroon'))))))
        plt.setp(stemlines, color=my_color, lw=30)
        # plt.setp(markers, color)
        plt.scatter(test.index, test[player], marker='o', s=1250, c=my_color, edgecolors='white', lw=4, zorder=12)
        plt.setp(baseline, linestyle="-", color="black", linewidth=10)
        baseline.set_xdata([0, 1])
        baseline.set_transform(plt.gca().get_yaxis_transform())

        # ax.annotate('test', xy=(.35,3.8), zorder=25)
        ax.tick_params(axis='x', direction='out', color='black', labelsize=12)
        ax.tick_params(axis='y', direction='out', color='black', labelsize=10)
        ax.grid(color='white', linestyle='solid', linewidth=2, alpha=.5)
        ax.set_facecolor('#595959')
        player_df['Age'] = int(player_df.Age)
        # plt.title(str(player)+' - '+str(position)+'\nMinutes Played: '+str(sum(player_df['Minutes played']))+'\nAge: '+str(sum(player_df['Age'])),
        #         fontproperties=titles)
        # plt.title(str(player) + ' - ' + str(position) + '\n' + '\n', fontproperties=titles)
        fig.text(.5, .935, str(player) + ' - ' + str(team) + ' - ' + str(position) + '\n' + '\n', fontproperties=titles,
                 horizontalalignment='center', verticalalignment='center')
        fig.text(.5, .935, 'Minutes Played: ' + str(sum(player_df['Minutes played'])), color='black',
                 fontproperties=subtitles,
                 horizontalalignment='center', verticalalignment='center')
        fig.text(.5, .9, 'Age: ' + str(sum(player_df['Age'])), color='black', fontproperties=subtitles,
                 horizontalalignment='center', verticalalignment='center')
        plt.ylabel('Z Score', fontproperties=labels)
        plt.yticks(fontproperties=labels)
        plt.xticks(my_range, test.index, fontproperties=labels)
        plt.xticks(rotation=25)
        plt.ylim(-3.75, 3.75)
        fig.text(.1, 0, 'Metrics Standardized by Position within League | ' + str(league), color='black',
                 fontproperties=labels)
        st.pyplot(fig)
        fn = str(player) + ' - ' + str(position) + ' - ' + str(league) + '.png'
        plt.savefig(fn, format='png', bbox_inches='tight')
        with open(fn, "rb") as file:
            btn = st.download_button(
                label="Download " + str(player) + "'s Graph",
                data=file,
                file_name=fn,
                mime="image/png"
            )
            hide_dataframe_row_index = """
                            <style>
                            .row_heading.level0 {display:none}
                            .blank {display:none}
                            </style>
                    """
        st.markdown(hide_dataframe_row_index, unsafe_allow_html=True)
        st.table(player_df)

        def convert_df(df):
            # IMPORTANT: Cache the conversion to prevent computation on every rerun
            return df.to_csv().encode('utf-8')

        # csv = convert_df(player_df)
        # st.download_button(label="Download data as CSV",data=csv,file_name='large_df.csv',mime='text/csv')
    elif position == 'AM-CM':
        position_df = league_df[(league_df['Position'].str.contains('AM', na=False))|(league_df['Position'].str.contains('CM', na=False))]
        filter_df = position_df[(position_df['Minutes played'] >= 350) & (position_df.Team.notnull())]
        player_data = pd.DataFrame(filter_df,
                                   columns=['Team', 'Player', 'Age', 'Minutes played', 'Non-penalty goals per 90',
                                            'xG per 90', 'Touches in box per 90', 'xA per 90', 'Assists per 90', 'Shot assists per 90', 'Second assists per 90',
                                            'Passes per 90', 'Accurate passes, %', 'Forward passes per 90', 'Accurate forward passes, %',
                                            'Passes to final third per 90', 'Progressive passes per 90', 'Passes to penalty area per 90',
                                            'Dribbles per 90', 'Progressive runs per 90',
                                            'Successful defensive actions per 90', 'PAdj Interceptions'
                                            ]).reset_index()
        col_list = ['Non-penalty goals per 90',
                                            'xG per 90', 'Touches in box per 90', 'xA per 90', 'Assists per 90', 'Shot assists per 90', 'Second assists per 90',
                                            'Passes per 90', 'Accurate passes, %', 'Forward passes per 90', 'Accurate forward passes, %',
                                            'Passes to final third per 90', 'Progressive passes per 90', 'Passes to penalty area per 90',
                                            'Dribbles per 90', 'Progressive runs per 90',
                                            'Successful defensive actions per 90', 'PAdj Interceptions']
        player_df = player_data
        player_data = player_data.fillna(0)

        player_data[col_list] = player_data[col_list].apply(zscore)
        # player_data = player_data.rename(columns={"xG per 90":"xG/90", "Non-penalty goals per 90":"Non-pen Goals/90",
        #                                         "Shots per 90":"Shots/90", "Touches in box per 90":"TouchesinBox/90",
        #                                        "Passes per 90":"Passes/90", "Accurate passes, %":"Pass%",
        #                                       "Passes to penalty area per 90":"PassesInto18/90",
        #                                      "Accurate passes to penalty area, %":"PassesInto18%", "Dribbles per 90":"Dribbles/90",
        #                                     "Progressive runs per 90":"ProgressiveRuns/90", "Aerial duels won, %":"Aerial%"})

        # st.dataframe(player_data)
        with col3:
            player = st.selectbox('Select Player', natsorted(player_data.Player.unique()))
        player_df = player_df[player_df['Player'] == (player)]
        player_df = player_df.drop(columns=['index'])
        team = player_df.Team.unique()
        team = (','.join(team))
        # player_data = player_data.apply(zscore)
        # player_data = player_data[player_data.Player == player]
        player_data = player_data.drop(columns=['index', 'Team', 'Age', 'Minutes played'])
        player_data = player_data.set_index('Player')
        test = player_data.transpose()
        my_range = range(0, len(test.index))
        fig, ax = plt.subplots(figsize=(22, 12), facecolor='#e6e6e6')
        markers, stemlines, baseline = plt.stem(test[player],
                                                bottom=0, use_line_collection=True, markerfmt=' ')
        # markerline.set_markerfacecolor('none')
        # plt.setp(baseline, visible=False)
        # my_color = np.where(test[player]>=0, 'darkblue', 'darkred')
        my_color = np.where((test[player] >= 2), 'darkblue',  # when... then
                            np.where((test[player] >= 1), 'dodgerblue',  # when... then
                                     np.where((test[player] >= 0), 'lightblue',  # when... then
                                              np.where((test[player] <= -2), 'darkred',  # when... then
                                                       np.where((test[player] <= -1), 'red',  # when... then
                                                                np.where((test[player] <= 0), 'coral',
                                                                         # when... then
                                                                         'maroon'))))))
        plt.setp(stemlines, color=my_color, lw=30)
        # plt.setp(markers, color)
        plt.scatter(test.index, test[player], marker='o', s=1250, c=my_color, edgecolors='white', lw=4, zorder=12)
        plt.setp(baseline, linestyle="-", color="black", linewidth=10)
        baseline.set_xdata([0, 1])
        baseline.set_transform(plt.gca().get_yaxis_transform())

        # ax.annotate('test', xy=(.35,3.8), zorder=25)
        ax.tick_params(axis='x', direction='out', color='black', labelsize=12)
        ax.tick_params(axis='y', direction='out', color='black', labelsize=10)
        ax.grid(color='white', linestyle='solid', linewidth=2, alpha=.5)
        ax.set_facecolor('#595959')
        player_df['Age'] = int(player_df.Age)
        # plt.title(str(player)+' - '+str(position)+'\nMinutes Played: '+str(sum(player_df['Minutes played']))+'\nAge: '+str(sum(player_df['Age'])),
        #         fontproperties=titles)
        # plt.title(str(player) + ' - ' + str(position) + '\n' + '\n', fontproperties=titles)
        fig.text(.5, .935, str(player) + ' - ' + str(team) + ' - ' + str(position) + '\n' + '\n', fontproperties=titles,
                 horizontalalignment='center', verticalalignment='center')
        fig.text(.5, .935, 'Minutes Played: ' + str(sum(player_df['Minutes played'])), color='black',
                 fontproperties=subtitles,
                 horizontalalignment='center', verticalalignment='center')
        fig.text(.5, .9, 'Age: ' + str(sum(player_df['Age'])), color='black', fontproperties=subtitles,
                 horizontalalignment='center', verticalalignment='center')
        plt.ylabel('Z Score', fontproperties=labels)
        plt.yticks(fontproperties=labels)
        plt.xticks(my_range, test.index, fontproperties=labels)
        plt.xticks(rotation=25)
        plt.ylim(-3.75, 3.75)
        fig.text(.1, 0, 'Metrics Standardized by Position within League | ' + str(league), color='black',
                 fontproperties=labels)
        st.pyplot(fig)
        fn = str(player) + ' - ' + str(position) + ' - ' + str(league) + '.png'
        plt.savefig(fn, format='png', bbox_inches='tight')
        with open(fn, "rb") as file:
            btn = st.download_button(
                label="Download " + str(player) + "'s Graph",
                data=file,
                file_name=fn,
                mime="image/png"
            )
            hide_dataframe_row_index = """
                                <style>
                                .row_heading.level0 {display:none}
                                .blank {display:none}
                                </style>
                        """
        st.markdown(hide_dataframe_row_index, unsafe_allow_html=True)
        st.table(player_df)

        def convert_df(df):
            # IMPORTANT: Cache the conversion to prevent computation on every rerun
            return df.to_csv().encode('utf-8')

        # csv = convert_df(player_df)
        # st.download_button(label="Download data as CSV",data=csv,file_name='large_df.csv',mime='text/csv')
    elif position == 'DM':
        position_df = league_df[(league_df['Position'].str.contains(position, na=False))]
        filter_df = position_df[(position_df['Minutes played'] >= 350) & (position_df.Team.notnull())]
        player_data = pd.DataFrame(filter_df,
                                   columns=['Team', 'Player', 'Age', 'Minutes played', 'Passes per 90', 'Accurate passes, %',
                                            'Forward passes per 90', 'Accurate forward passes, %',  'Passes to final third per 90', 'Accurate passes to final third, %',
                                            'Passes to penalty area per 90', 'Progressive passes per 90', 'Through passes per 90','Dribbles per 90',
                                            'Progressive runs per 90', 'Successful defensive actions per 90', 'Defensive duels won, %',
                                            'Aerial duels per 90', 'Aerial duels won, %', 'PAdj Interceptions'
                                            ]).reset_index()
        col_list = [ 'Passes per 90', 'Accurate passes, %',
                                            'Forward passes per 90', 'Accurate forward passes, %',  'Passes to final third per 90', 'Accurate passes to final third, %',
                                            'Passes to penalty area per 90', 'Progressive passes per 90', 'Through passes per 90','Dribbles per 90',
                                            'Progressive runs per 90', 'Successful defensive actions per 90', 'Defensive duels won, %',
                                            'Aerial duels per 90', 'Aerial duels won, %', 'PAdj Interceptions']
        player_df = player_data
        player_data = player_data.fillna(0)

        player_data[col_list] = player_data[col_list].apply(zscore)
        # player_data = player_data.rename(columns={"xG per 90":"xG/90", "Non-penalty goals per 90":"Non-pen Goals/90",
        #                                         "Shots per 90":"Shots/90", "Touches in box per 90":"TouchesinBox/90",
        #                                        "Passes per 90":"Passes/90", "Accurate passes, %":"Pass%",
        #                                       "Passes to penalty area per 90":"PassesInto18/90",
        #                                      "Accurate passes to penalty area, %":"PassesInto18%", "Dribbles per 90":"Dribbles/90",
        #                                     "Progressive runs per 90":"ProgressiveRuns/90", "Aerial duels won, %":"Aerial%"})

        # st.dataframe(player_data)
        with col3:
            player = st.selectbox('Select Player', natsorted(player_data.Player.unique()))
        player_df = player_df[player_df['Player'] == (player)]
        player_df = player_df.drop(columns=['index'])
        team = player_df.Team.unique()
        team = (','.join(team))
        # player_data = player_data.apply(zscore)
        # player_data = player_data[player_data.Player == player]
        player_data = player_data.drop(columns=['index', 'Team', 'Age', 'Minutes played'])
        player_data = player_data.set_index('Player')
        test = player_data.transpose()
        my_range = range(0, len(test.index))
        fig, ax = plt.subplots(figsize=(22, 12), facecolor='#e6e6e6')
        markers, stemlines, baseline = plt.stem(test[player],
                                                bottom=0, use_line_collection=True, markerfmt=' ')
        # markerline.set_markerfacecolor('none')
        # plt.setp(baseline, visible=False)
        # my_color = np.where(test[player]>=0, 'darkblue', 'darkred')
        my_color = np.where((test[player] >= 2), 'darkblue',  # when... then
                            np.where((test[player] >= 1), 'dodgerblue',  # when... then
                                     np.where((test[player] >= 0), 'lightblue',  # when... then
                                              np.where((test[player] <= -2), 'darkred',  # when... then
                                                       np.where((test[player] <= -1), 'red',  # when... then
                                                                np.where((test[player] <= 0), 'coral',
                                                                         # when... then
                                                                         'maroon'))))))
        plt.setp(stemlines, color=my_color, lw=30)
        # plt.setp(markers, color)
        plt.scatter(test.index, test[player], marker='o', s=1250, c=my_color, edgecolors='white', lw=4, zorder=12)
        plt.setp(baseline, linestyle="-", color="black", linewidth=10)
        baseline.set_xdata([0, 1])
        baseline.set_transform(plt.gca().get_yaxis_transform())

        # ax.annotate('test', xy=(.35,3.8), zorder=25)
        ax.tick_params(axis='x', direction='out', color='black', labelsize=12)
        ax.tick_params(axis='y', direction='out', color='black', labelsize=10)
        ax.grid(color='white', linestyle='solid', linewidth=2, alpha=.5)
        ax.set_facecolor('#595959')
        player_df['Age'] = int(player_df.Age)
        # plt.title(str(player)+' - '+str(position)+'\nMinutes Played: '+str(sum(player_df['Minutes played']))+'\nAge: '+str(sum(player_df['Age'])),
        #         fontproperties=titles)
        # plt.title(str(player) + ' - ' + str(position) + '\n' + '\n', fontproperties=titles)
        fig.text(.5, .935, str(player) + ' - ' + str(team) + ' - ' + str(position) + '\n' + '\n', fontproperties=titles,
                 horizontalalignment='center', verticalalignment='center')
        fig.text(.5, .935, 'Minutes Played: ' + str(sum(player_df['Minutes played'])), color='black',
                 fontproperties=subtitles,
                 horizontalalignment='center', verticalalignment='center')
        fig.text(.5, .9, 'Age: ' + str(sum(player_df['Age'])), color='black', fontproperties=subtitles,
                 horizontalalignment='center', verticalalignment='center')
        plt.ylabel('Z Score', fontproperties=labels)
        plt.yticks(fontproperties=labels)
        plt.xticks(my_range, test.index, fontproperties=labels)
        plt.xticks(rotation=25)
        plt.ylim(-3.75, 3.75)
        fig.text(.1, 0, 'Metrics Standardized by Position within League | ' + str(league), color='black',
                 fontproperties=labels)
        st.pyplot(fig)
        fn = str(player) + ' - ' + str(position) + ' - ' + str(league) + '.png'
        plt.savefig(fn, format='png', bbox_inches='tight')
        with open(fn, "rb") as file:
            btn = st.download_button(
                label="Download " + str(player) + "'s Graph",
                data=file,
                file_name=fn,
                mime="image/png"
            )
            hide_dataframe_row_index = """
                                <style>
                                .row_heading.level0 {display:none}
                                .blank {display:none}
                                </style>
                        """
        st.markdown(hide_dataframe_row_index, unsafe_allow_html=True)
        st.table(player_df)

        def convert_df(df):
            # IMPORTANT: Cache the conversion to prevent computation on every rerun
            return df.to_csv().encode('utf-8')

        # csv = convert_df(player_df)
        # st.download_button(label="Download data as CSV",data=csv,file_name='large_df.csv',mime='text/csv')
    elif position == 'FB':
        position_df = league_df[(league_df['Position'].str.contains('LB', na=False))|(league_df['Position'].str.contains('RB', na=False))]
        filter_df = position_df[(position_df['Minutes played'] >= 350) & (position_df.Team.notnull())]
        player_data = pd.DataFrame(filter_df,
                                   columns=['Team', 'Player', 'Age', 'Minutes played', 'Passes per 90', 'Accurate passes, %',
                                            'Forward passes per 90', 'Accurate forward passes, %',  'Passes to final third per 90', 'Accurate passes to final third, %',
                                            'Passes to penalty area per 90', 'Accurate passes to penalty area, %', 'Progressive passes per 90', 'Dribbles per 90',
                                            'Progressive runs per 90', 'Successful defensive actions per 90', 'Defensive duels won, %',
                                            'Aerial duels per 90', 'Aerial duels won, %', 'PAdj Interceptions'
                                            ]).reset_index()
        col_list = ['Passes per 90', 'Accurate passes, %',
                                            'Forward passes per 90', 'Accurate forward passes, %',  'Passes to final third per 90', 'Accurate passes to final third, %',
                                            'Passes to penalty area per 90', 'Accurate passes to penalty area, %', 'Progressive passes per 90', 'Dribbles per 90',
                                            'Progressive runs per 90', 'Successful defensive actions per 90', 'Defensive duels won, %',
                                            'Aerial duels per 90', 'Aerial duels won, %', 'PAdj Interceptions']
        player_df = player_data
        player_data = player_data.fillna(0)

        player_data[col_list] = player_data[col_list].apply(zscore)
        # player_data = player_data.rename(columns={"xG per 90":"xG/90", "Non-penalty goals per 90":"Non-pen Goals/90",
        #                                         "Shots per 90":"Shots/90", "Touches in box per 90":"TouchesinBox/90",
        #                                        "Passes per 90":"Passes/90", "Accurate passes, %":"Pass%",
        #                                       "Passes to penalty area per 90":"PassesInto18/90",
        #                                      "Accurate passes to penalty area, %":"PassesInto18%", "Dribbles per 90":"Dribbles/90",
        #                                     "Progressive runs per 90":"ProgressiveRuns/90", "Aerial duels won, %":"Aerial%"})

        # st.dataframe(player_data)
        with col3:
            player = st.selectbox('Select Player', natsorted(player_data.Player.unique()))
        player_df = player_df[player_df['Player'] == (player)]
        player_df = player_df.drop(columns=['index'])
        team = player_df.Team.unique()
        team = (','.join(team))
        # player_data = player_data.apply(zscore)
        # player_data = player_data[player_data.Player == player]
        player_data = player_data.drop(columns=['index', 'Team', 'Age', 'Minutes played'])
        player_data = player_data.set_index('Player')
        test = player_data.transpose()
        my_range = range(0, len(test.index))
        fig, ax = plt.subplots(figsize=(22, 12), facecolor='#e6e6e6')
        markers, stemlines, baseline = plt.stem(test[player],
                                                bottom=0, use_line_collection=True, markerfmt=' ')
        # markerline.set_markerfacecolor('none')
        # plt.setp(baseline, visible=False)
        # my_color = np.where(test[player]>=0, 'darkblue', 'darkred')
        my_color = np.where((test[player] >= 2), 'darkblue',  # when... then
                            np.where((test[player] >= 1), 'dodgerblue',  # when... then
                                     np.where((test[player] >= 0), 'lightblue',  # when... then
                                              np.where((test[player] <= -2), 'darkred',  # when... then
                                                       np.where((test[player] <= -1), 'red',  # when... then
                                                                np.where((test[player] <= 0), 'coral',
                                                                         # when... then
                                                                         'maroon'))))))
        plt.setp(stemlines, color=my_color, lw=30)
        # plt.setp(markers, color)
        plt.scatter(test.index, test[player], marker='o', s=1250, c=my_color, edgecolors='white', lw=4, zorder=12)
        plt.setp(baseline, linestyle="-", color="black", linewidth=10)
        baseline.set_xdata([0, 1])
        baseline.set_transform(plt.gca().get_yaxis_transform())

        # ax.annotate('test', xy=(.35,3.8), zorder=25)
        ax.tick_params(axis='x', direction='out', color='black', labelsize=12)
        ax.tick_params(axis='y', direction='out', color='black', labelsize=10)
        ax.grid(color='white', linestyle='solid', linewidth=2, alpha=.5)
        ax.set_facecolor('#595959')
        player_df['Age'] = int(player_df.Age)
        # plt.title(str(player)+' - '+str(position)+'\nMinutes Played: '+str(sum(player_df['Minutes played']))+'\nAge: '+str(sum(player_df['Age'])),
        #         fontproperties=titles)
        # plt.title(str(player) + ' - ' + str(position) + '\n' + '\n', fontproperties=titles)
        fig.text(.5, .935, str(player) + ' - ' + str(team) + ' - ' + str(position) + '\n' + '\n', fontproperties=titles,
                 horizontalalignment='center', verticalalignment='center')
        fig.text(.5, .935, 'Minutes Played: ' + str(sum(player_df['Minutes played'])), color='black',
                 fontproperties=subtitles,
                 horizontalalignment='center', verticalalignment='center')
        fig.text(.5, .9, 'Age: ' + str(sum(player_df['Age'])), color='black', fontproperties=subtitles,
                 horizontalalignment='center', verticalalignment='center')
        plt.ylabel('Z Score', fontproperties=labels)
        plt.yticks(fontproperties=labels)
        plt.xticks(my_range, test.index, fontproperties=labels)
        plt.xticks(rotation=25)
        plt.ylim(-3.75, 3.75)
        fig.text(.1, 0, 'Metrics Standardized by Position within League | ' + str(league), color='black',
                 fontproperties=labels)
        st.pyplot(fig)
        fn = str(player) + ' - ' + str(position) + ' - ' + str(league) + '.png'
        plt.savefig(fn, format='png', bbox_inches='tight')
        with open(fn, "rb") as file:
            btn = st.download_button(
                label="Download " + str(player) + "'s Graph",
                data=file,
                file_name=fn,
                mime="image/png"
            )
            hide_dataframe_row_index = """
                                <style>
                                .row_heading.level0 {display:none}
                                .blank {display:none}
                                </style>
                        """
        st.markdown(hide_dataframe_row_index, unsafe_allow_html=True)
        st.table(player_df)

        def convert_df(df):
            # IMPORTANT: Cache the conversion to prevent computation on every rerun
            return df.to_csv().encode('utf-8')

        # csv = convert_df(player_df)
        # st.download_button(label="Download data as CSV",data=csv,file_name='large_df.csv',mime='text/csv')
    else:
        position_df = league_df[(league_df['Position'].str.contains('CB', na=False))]
        filter_df = position_df[(position_df['Minutes played'] >= 350) & (position_df.Team.notnull())]
        player_data = pd.DataFrame(filter_df,
                                   columns=['Team', 'Player', 'Age', 'Minutes played', 'Passes per 90', 'Accurate passes, %',
                                            'Forward passes per 90', 'Accurate forward passes, %',  'Progressive passes per 90',
                                            'Long passes per 90', 'Duels per 90', 'Duels won, %', 'Dribbles per 90',
                                            'Successful defensive actions per 90', 'Defensive duels won, %',
                                            'Aerial duels per 90', 'Aerial duels won, %', 'PAdj Interceptions', 'Shots blocked per 90'
                                            ]).reset_index()
        col_list = ['Passes per 90', 'Accurate passes, %',
                                            'Forward passes per 90', 'Accurate forward passes, %',  'Progressive passes per 90',
                                            'Long passes per 90', 'Duels per 90', 'Duels won, %', 'Dribbles per 90',
                                            'Successful defensive actions per 90', 'Defensive duels won, %',
                                            'Aerial duels per 90', 'Aerial duels won, %', 'PAdj Interceptions', 'Shots blocked per 90']
        player_df = player_data
        player_data = player_data.fillna(0)

        player_data[col_list] = player_data[col_list].apply(zscore)
        # player_data = player_data.rename(columns={"xG per 90":"xG/90", "Non-penalty goals per 90":"Non-pen Goals/90",
        #                                         "Shots per 90":"Shots/90", "Touches in box per 90":"TouchesinBox/90",
        #                                        "Passes per 90":"Passes/90", "Accurate passes, %":"Pass%",
        #                                       "Passes to penalty area per 90":"PassesInto18/90",
        #                                      "Accurate passes to penalty area, %":"PassesInto18%", "Dribbles per 90":"Dribbles/90",
        #                                     "Progressive runs per 90":"ProgressiveRuns/90", "Aerial duels won, %":"Aerial%"})

        # st.dataframe(player_data)
        with col3:
            player = st.selectbox('Select Player', natsorted(player_data.Player.unique()))
        player_df = player_df[player_df['Player'] == (player)]
        player_df = player_df.drop(columns=['index'])
        team = player_df.Team.unique()
        team = (','.join(team))
        # player_data = player_data.apply(zscore)
        # player_data = player_data[player_data.Player == player]
        player_data = player_data.drop(columns=['index', 'Team', 'Age', 'Minutes played'])
        player_data = player_data.set_index('Player')
        test = player_data.transpose()
        my_range = range(0, len(test.index))
        fig, ax = plt.subplots(figsize=(22, 12), facecolor='#e6e6e6')
        markers, stemlines, baseline = plt.stem(test[player],
                                                bottom=0, use_line_collection=True, markerfmt=' ')
        # markerline.set_markerfacecolor('none')
        # plt.setp(baseline, visible=False)
        # my_color = np.where(test[player]>=0, 'darkblue', 'darkred')
        my_color = np.where((test[player] >= 2), 'darkblue',  # when... then
                            np.where((test[player] >= 1), 'dodgerblue',  # when... then
                                     np.where((test[player] >= 0), 'lightblue',  # when... then
                                              np.where((test[player] <= -2), 'darkred',  # when... then
                                                       np.where((test[player] <= -1), 'red',  # when... then
                                                                np.where((test[player] <= 0), 'coral',
                                                                         # when... then
                                                                         'maroon'))))))
        plt.setp(stemlines, color=my_color, lw=30)
        # plt.setp(markers, color)
        plt.scatter(test.index, test[player], marker='o', s=1250, c=my_color, edgecolors='white', lw=4, zorder=12)
        plt.setp(baseline, linestyle="-", color="black", linewidth=10)
        baseline.set_xdata([0, 1])
        baseline.set_transform(plt.gca().get_yaxis_transform())

        # ax.annotate('test', xy=(.35,3.8), zorder=25)
        ax.tick_params(axis='x', direction='out', color='black', labelsize=12)
        ax.tick_params(axis='y', direction='out', color='black', labelsize=10)
        ax.grid(color='white', linestyle='solid', linewidth=2, alpha=.5)
        ax.set_facecolor('#595959')
        player_df['Age'] = int(player_df.Age)
        # plt.title(str(player)+' - '+str(position)+'\nMinutes Played: '+str(sum(player_df['Minutes played']))+'\nAge: '+str(sum(player_df['Age'])),
        #         fontproperties=titles)
        # plt.title(str(player) + ' - ' + str(position) + '\n' + '\n', fontproperties=titles)
        fig.text(.5, .935, str(player) + ' - ' + str(team) + ' - ' + str(position) + '\n' + '\n', fontproperties=titles,
                 horizontalalignment='center', verticalalignment='center')
        fig.text(.5, .935, 'Minutes Played: ' + str(sum(player_df['Minutes played'])), color='black',
                 fontproperties=subtitles,
                 horizontalalignment='center', verticalalignment='center')
        fig.text(.5, .9, 'Age: ' + str(sum(player_df['Age'])), color='black', fontproperties=subtitles,
                 horizontalalignment='center', verticalalignment='center')
        plt.ylabel('Z Score', fontproperties=labels)
        plt.yticks(fontproperties=labels)
        plt.xticks(my_range, test.index, fontproperties=labels)
        plt.xticks(rotation=25)
        plt.ylim(-3.75, 3.75)
        fig.text(.1, 0, 'Metrics Standardized by Position within League | ' + str(league), color='black',
                 fontproperties=labels)
        st.pyplot(fig)
        fn = str(player) + ' - ' + str(position) + ' - ' + str(league) + '.png'
        plt.savefig(fn, format='png', bbox_inches='tight')
        with open(fn, "rb") as file:
            btn = st.download_button(
                label="Download " + str(player) + "'s Graph",
                data=file,
                file_name=fn,
                mime="image/png"
            )
            hide_dataframe_row_index = """
                                <style>
                                .row_heading.level0 {display:none}
                                .blank {display:none}
                                </style>
                        """
        st.markdown(hide_dataframe_row_index, unsafe_allow_html=True)
        st.table(player_df)

        def convert_df(df):
            # IMPORTANT: Cache the conversion to prevent computation on every rerun
            return df.to_csv().encode('utf-8')

        # csv = convert_df(player_df)
        # st.download_button(label="Download data as CSV",data=csv,file_name='large_df.csv',mime='text/csv')

st.set_page_config(layout="wide", page_title='Wave Recruitment App', initial_sidebar_state='collapsed')


if __name__ == "__main__":
    main()

#st.set_option('server.enableCORS', True)
# to run : streamlit run "/Users/michaelpoma/Documents/Python/Codes/Wave Recruitment App.py"


