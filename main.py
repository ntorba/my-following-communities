import os
import requests
import pandas as pd
from twarc import Twarc2
import streamlit as st
import plotly.express as px
from dotenv import load_dotenv

from save_following import save_following_to_csv, get_cluster_info

load_dotenv()

twarc = Twarc2(bearer_token=os.environ["TWITTER_TOKEN"])

st.subheader('What is this?')
st.write("This app is uses the api provided by [Hive](hive.one) to show the community landscape of who we follow on twitter. "
    "The 'community landscape' is a visualization of which communities the people followed by a user are a part of, according to hive. \n"
)
st.write(
    "I made this to help me understand the types of information I should expect from my twitter timeline (e.g. if I follow a bunch of people "
    "talking about 'PKM' I should expect to see a lot of tweets about 'PKM' in my timeline). \n"
    "I also want to use this to help me understand the interests of others (and hopefully find some cool accounts in cool communities I'm less aware of."
)


st.title("The Borg Community Landscape of who we follow on twitter")
# streamlit dropdown of usernames for any users that have two csv's in the data/ directory
usernames = list(set([file.split("--")[0] for file in os.listdir("data/") if file.endswith(".csv")]))
# username = st.selectbox("Select a username", usernames)

username_select_box = st.selectbox("Select pre-loaded user (selecting a user from this dropdown will load data muuuuch faster)", [None] + usernames)

# get streamlit text input
username_text_input = st.text_input("Load new user (takes much longer to load - might hit rate limit issues if a lot of you are using this at once)", value=username_select_box)

username = None
if username_select_box is not None:
    username = username_select_box
if username_text_input is not None:
    # this SHOULD overwrite the username if it was set by the selectbox
    username = username_text_input

if username == "None": # TODO: wtf is happening here..?
    st.write("Please select a username from the dropdown or enter a username in the text box")
    st.stop()

gen = twarc.user_lookup(users=[username], usernames=True) 
data = [i for i in gen][0]

if "errors" in data:
    st.write(f"User {username} not found, please try again.")
else: 
    user_id = data["data"][0]["id"]
    # check if file f"data/{username}_following.csv" exists
    if not os.path.exists(f"data/{username}--following.csv"):
        # if it doesn't exist, run save_following_to_csv
        # create a streamlit progress bar
        with st.spinner("Loading follows from twitter"):
            following_df = save_following_to_csv(user_id, username)
        with st.spinner("Loading community info from borg (this can take some time, especially if the user follows a lot of accounts)"):
            borg_community_df = get_cluster_info(following_df)
            borg_community_df.to_csv(f"data/{username}--borg_community_info.csv", index=False)

    else:
        # if it does exist, load the csv into a dataframe
        following_df = pd.read_csv(f"data/{username}--following.csv")
        borg_community_df = pd.read_csv(f"data/{username}--borg_community_info.csv")
    

    # streamlit table that displays the dataframe
    st.subheader(f"Showing community distribution of the accounts {username} follows")
    st.write(f'**{username}** follows {len(following_df)} users')

    # streamlit button that allows me to download the csv
    st.download_button(label=f"Download CSV of who **{username}** follows", data=following_df.to_csv(index=False), file_name=f"data/{username}_following.csv", mime="text/csv")
    st.download_button(label=f"Download CSV of community aggregation for **{username}**", data=borg_community_df.to_csv(index=False), file_name=f"data/{username}_following.csv", mime="text/csv")

    st.write(f'{borg_community_df[borg_community_df["clusters.name"].isna()].shape[0]} users {username} follows are not included in any clusters.')

    st.write(f'Users **{username}** follows are included in {borg_community_df["clusters.name"].nunique()} unique communities.')


    # streamlit select range of top communities to display


    st.subheader("Community Distribution")
    min_num_communities, max_num_communities = st.slider("use this slider to select the number of top communities to display", min_value=0, max_value=borg_community_df["clusters.name"].nunique(), value=(0,20), step=5)
    community_grouping = borg_community_df.groupby('clusters.name').agg({'username': 'count'}, dropna=False).reset_index().sort_values('username', ascending=False)


    fig = px.bar(
        community_grouping.iloc[min_num_communities:max_num_communities], 
        x="clusters.name", 
        y="username", 
        color="clusters.name", 
        title=f"Community distribution of the accounts {username} follows"
    )
    st.plotly_chart(fig)


    st.subheader("Show users by community")
    community = st.selectbox("Select a community", community_grouping['clusters.name'].unique())
    specific_community = borg_community_df[borg_community_df['clusters.name'] == community][["username", "latest_scores.rank"]].sort_values("latest_scores.rank", ascending=True)
    specific_community["latest_scores.rank"] = specific_community["latest_scores.rank"].astype(int)
    specific_community["profile_url"] = specific_community["username"].apply(lambda x: f"https://twitter.com/{x}")
    st.write(f"{username} follows {specific_community.shape[0]} users in the {community} community, with an average rank of {round(specific_community['latest_scores.rank'].mean())}")
    st.dataframe(specific_community)


    st.subheader("Users in multiple communities")
    # get streamlit number input for minimum number of communities a user must belong in
    group = borg_community_df.groupby("username").agg({"clusters.name": "count"}).reset_index().sort_values("clusters.name", ascending=False)
    min_num_communities = st.number_input("Enter the minimum number of communities a user must belong in", value=2, min_value=2, max_value=group["clusters.name"].max(), step=1)
    min_group = group[group["clusters.name"] >= min_num_communities]
    st.dataframe(min_group)

    # select username from dropdown 
    investigate_username = st.selectbox("Select a username to see which communities they belong to", min_group["username"].unique())
    # get the communities that user belongs in
    user_communities = borg_community_df[borg_community_df["username"] == investigate_username][["clusters.name", "latest_scores.rank"]].sort_values("latest_scores.rank", ascending=True)
    user_communities['latest_scores.rank'] = user_communities['latest_scores.rank'].astype(int)
    st.write(user_communities)
