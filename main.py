import os
import requests
import pandas as pd
from twarc import Twarc2
import streamlit as st
import plotly.express as px
from dotenv import load_dotenv

load_dotenv()

twarc = Twarc2(bearer_token=os.environ["TWITTER_TOKEN"])

st.title("See the Borg Community Landscape of who you follow on twitter")

# streamlit dropdown of usernames for any users that have two csv's in the data/ directory
usernames = list(set([file.split("_")[0] for file in os.listdir("data/") if file.endswith(".csv")]))
username = st.selectbox("Select a username", usernames)

# load both csv's into pandas dataframes
following_df = pd.read_csv(f"data/{username}_following.csv")
borg_community_df = pd.read_csv(f"data/{username}_borg_community_info.csv")

# streamlit table that displays the dataframe
st.write(f'{username} follows {len(following_df)} users')

# streamlit button that allows me to download the csv
st.download_button(label=f"Download CSV of who {username} follows", data=following_df.to_csv(index=False), file_name="data/{username}_following.csv", mime="text/csv")
st.download_button(label=f"Download CSV community aggregation for {username}", data=borg_community_df.to_csv(index=False), file_name="data/{username}_following.csv", mime="text/csv")

st.write(f'{borg_community_df[borg_community_df["clusters.name"].isna()].shape[0]} users you follow are not included in any clusters.')

st.write(f'Users you follow are included in {borg_community_df["clusters.name"].nunique()} unique communities.')


# streamlit select range of top communities to display


min_num_communities, max_num_communities = st.slider("Select number of top communities to display", min_value=0, max_value=borg_community_df["clusters.name"].nunique(), value=(0,20), step=5)
community_grouping = borg_community_df.groupby('clusters.name').agg({'username': 'count'}, dropna=False).reset_index().sort_values('username', ascending=False)


fig = px.bar(
    community_grouping.iloc[min_num_communities:max_num_communities], 
    x="clusters.name", 
    y="username", 
    color="clusters.name", 
    title=f"Num users in hive community"
)
st.plotly_chart(fig)


st.subheader("Show users by community")
community = st.selectbox("Select a community", community_grouping['clusters.name'].unique())
specific_community = borg_community_df[borg_community_df['clusters.name'] == community][["username", "latest_scores.rank"]].sort_values("latest_scores.rank", ascending=True)
specific_community["latest_scores.rank"] = specific_community["latest_scores.rank"].astype(int)
st.write(f"You follow {specific_community.shape[0]} users in the {community} community, with an average rank of {round(specific_community['latest_scores.rank'].mean())}")
st.table(specific_community)