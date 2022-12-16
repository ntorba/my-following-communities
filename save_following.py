

import os
import concurrent.futures
import requests
import pandas as pd
from twarc import Twarc2
from twarc_csv import DataFrameConverter
import streamlit as st
import click
from dotenv import load_dotenv

load_dotenv()

twarc = Twarc2(bearer_token=os.environ["TWITTER_TOKEN"])
converter = DataFrameConverter(input_data_type="users", allow_duplicates=False)   

BORG_API_ENDPOINT = "https://api.borg.id/influence/influencers/twitter:{}/"

# create click group
@click.group()
def cli():
    pass

# use twarc to get the users a user follows
def get_following(user_id):
    following = []
    for page in twarc.following(user_id):
        page_df = converter.process([page])
        following.append(page_df)
    return pd.concat(following)

# save the users that nicktorba follows to a csv
def save_following_to_csv(user_id, username):
    following_df = get_following(user_id)
    following_df.to_csv(f"data/{username}_following.csv", index=False)
    return following_df

# function that makes a request to the borg api, with the user id inserted, and returns the response
def get_borg_influence(user):
    # make borg request with BORG_API_KEY env var included in request headers 
    response = requests.get(BORG_API_ENDPOINT.format(user["id"]), headers={"Authorization": f'Token {os.environ["BORG_API_KEY"]}'})
    return user, response.json()

def get_cluster_info(df):
    df_rows = []
    # use conncurrent.futures to make requests to the borg api in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
        futures = [executor.submit(get_borg_influence, user) for user in df.to_dict(orient="records")]
        my_bar = st.progress(0)
        total = df.shape[0]
        count = 0
        for future in concurrent.futures.as_completed(futures):
            user, borg_influence = future.result()
            if 'error' in borg_influence:
                print(f"user {user['username']} is not indexed by borg")
                df_rows.append(user)
                continue
            clusters = borg_influence.get("clusters", [])
            if len(clusters) < 0:
                # get the row from df where id == user_id as a dict
                df_rows.append(user)
                continue

            clusters_by_id = {cluster["id"]: cluster for cluster in clusters}

            latest_scores = borg_influence["latest_scores"]

            for score_dict in latest_scores:
                cluster_id = score_dict["cluster_id"]
                score_dict = {f'latest_scores.{key}': value for key, value in score_dict.items()}
                cluster = clusters_by_id[cluster_id]
                cluster = {f'clusters.{key}': value for key, value in cluster.items()}
                row = {**score_dict, **cluster, **user}
                df_rows.append(row)
            count += 1
            my_bar.progress(count/total)
    return pd.DataFrame(df_rows)



# a click function to save the users that a user follows to a csv
@cli.command()
@click.option("--username", default="nicktorba", help="The name of the user whose following you want to save")
def save_following(username):
    # use twarc to get the user_id from username
    gen = twarc.user_lookup(users=[username], usernames=True) 
    data = [i for i in gen]
    user_id = data[0]["data"][0]["id"]
    df = save_following_to_csv(user_id, username)
    com_df = get_cluster_info(df)
    # use twarc to get the user_id from username
    com_df.to_csv(f"data/{username}_borg_community_info.csv", index=False)

    
if __name__ == "__main__":
    cli()