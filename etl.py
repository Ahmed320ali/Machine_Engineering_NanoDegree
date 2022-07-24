import os
import glob
import psycopg2
import pandas as pd
from sql_queries import *


def process_song_file(cur, filepath):
    """
    Description: This function is responsible for reading the file into a dataframe given file path. Then insert song and artist data into                  their respective tables.

    Arguments:
        cur: the cursor object.
        filepath: log data or song data file path.

    Returns:
        None
    """
    # open song file
    df = pd.read_json(filepath, lines = True)

    # insert song record
    song_data = df[['song_id','title','artist_id','year','duration']].values
    song_data = song_data[0].tolist()
    cur.execute(song_table_insert, song_data)
    
    # insert artist record
    artist_data = df[['artist_id','artist_name','artist_location','artist_latitude','artist_longitude']].values
    artist_data = artist_data[0].tolist()
    cur.execute(artist_table_insert, artist_data)


def process_log_file(cur, filepath):
    """
    Description: This function is responsible for reading the file into a dataframe given file path. Filter by nextson action. Then                        extract (datetime - year - month - week - day - hour - week day). Then insert data into time, user, songplays tables.
    Arguments:
        cur: the cursor object.
        filepath: log data or song data file path.

    Returns:
        None
    """
    # open log file
    df = pd.read_json(filepath, lines = True)

    # filter by NextSong action
    df = df.loc[df["page"] == "NextSong"]

    # convert timestamp column to datetime
    t = df.copy()
    t['nts'] =  pd.to_datetime(t['ts'], unit='ms')
    t['year'] = pd.DatetimeIndex(t['nts']).year
    t['month'] = pd.DatetimeIndex(t['nts']).month
    t['week'] = pd.DatetimeIndex(t['nts']).week
    t['day'] = pd.DatetimeIndex(t['nts']).day
    t['hour'] = pd.DatetimeIndex(t['nts']).hour
    t['week_day'] = pd.DatetimeIndex(t['nts']).weekday_name
    
    # insert time data records
    time_data = ('nts', 'hour', 'day', 'week', 'month', 'year', 'week_day')
    column_labels = ('start_time', 'hour', 'day', 'week', 'month', 'year', 'weekday')
    time_df = t[['nts', 'hour', 'day', 'week', 'month', 'year', 'week_day']]

    for i, row in time_df.iterrows():
        cur.execute(time_table_insert, list(row))

    # load user table
    user_df = t[['userId', 'firstName', 'lastName', 'gender', 'level']]

    # insert user records
    for i, row in user_df.iterrows():
        cur.execute(user_table_insert, row)

    # insert songplay records
    for index, row in t.iterrows():
        
        # get songid and artistid from song and artist tables
        cur.execute(song_select, (row.song, row.artist, row.length))
        results = cur.fetchone()
        
        if results:
            songid, artistid = results
        else:
            songid, artistid = None, None

        # insert songplay record
        songplay_data = (row.nts, row.userId, row.level, songid, artistid, row.itemInSession, row.location, row.userAgent)
        cur.execute(songplay_table_insert, songplay_data)


def process_data(cur, conn, filepath, func):
    """
    Description: This function is responsible for getting the file path and type of function as a parameter. Then get all the files paths                  in the given path that ends with json and add it to a list. Then it feeds the function that inserts data into database a                  file at a time.

    Arguments:
        cur: the cursor object.
        conn: connection to the database.
        filepath: log data or song data file path.
        func: type of function that transforms the data and inserts it into the database.

    Returns:
        None
    """
    # get all files matching extension from directory
    all_files = []
    for root, dirs, files in os.walk(filepath):
        files = glob.glob(os.path.join(root,'*.json'))
        for f in files :
            all_files.append(os.path.abspath(f))

    # get total number of files found
    num_files = len(all_files)
    print('{} files found in {}'.format(num_files, filepath))

    # iterate over files and process
    for i, datafile in enumerate(all_files, 1):
        func(cur, datafile)
        conn.commit()
        print('{}/{} files processed.'.format(i, num_files))


def main():
    conn = psycopg2.connect("host=127.0.0.1 dbname=sparkifydb user=student password=student")
    cur = conn.cursor()

    process_data(cur, conn, filepath='data/song_data', func=process_song_file)
    process_data(cur, conn, filepath='data/log_data', func=process_log_file)

    conn.close()


if __name__ == "__main__":
    main()