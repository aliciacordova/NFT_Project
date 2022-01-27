
#########################################################################################
# IMPORT DEPENDENCIES
#########################################################################################

# Import Dependencies
from flask import Flask, render_template, jsonify, json, request, redirect, url_for
from flask_pymongo import PyMongo
import pymongo

from bson.json_util import dumps
import json
import pandas as pd
import random

# Import MongoDB and AWS access paramaters
from config import user, password, key_id, secret_access_key

# Import plotting libraries
import networkx as nx 
import plotly.graph_objects as go
from textwrap import wrap
import matplotlib
import matplotlib.pyplot as plt
# Use matplotlib back-end
matplotlib.use('Agg')

# Import AWS SDK
import boto3

#########################################################################################



##############################################
# BUILD THE CRYPTO PUNKS FACTS 
##############################################
def punkFacts(id_selection):

    # construct the connection string for Atlas
    CONNECTION_STRING = "mongodb+srv://"+ user + ":" + password +"@cluster0.wddnt.mongodb.net/crypto_punks_mdb?retryWrites=true&w=majority"
    # Create the connection client to Atlas
    client = pymongo.MongoClient(CONNECTION_STRING) 
    # indicate the database to access in Atlas
    db = pymongo.database.Database(client,'crypto_punks_mdb')
    # assign the connection to the database and collection to variables (i.e. this still is not 'reading' 
    # the data from the database)
    attributes = pymongo.collection.Collection(db, 'attributes_col')
    crypto_punks = pymongo.collection.Collection(db, 'crypto_punks_col')

    # search the database for the unique punk_id value provided as input to 
    # the function and assign the output to a variable. The output will be an object.
    crypto_punks_data = json.loads(dumps(crypto_punks.find({"punk_id":id_selection}))) #[Replace "3600" for sample in the final code]
    
    # import the list of all crypto punk attributes
    attributes_data = json.loads(dumps(attributes.find()))
    
    # Convert the json lists to dataframes and drop un-needed columns
    punks_df = pd.DataFrame(crypto_punks_data)
    punks_df = punks_df.drop(columns=["_id"])
    attributes_df = pd.DataFrame(attributes_data)
    attributes_df = attributes_df.drop(columns=["_id"])

    # Create the summary punk_facts dataframe
    # 1. Create an empty list for all the attributes in the punk_id
    punk_attribute_list = []

    # 2. Populate the list
    punk_attribute_list.append(punks_df.at[0,"type"])
    punk_accessories = punks_df.at[0,"accessories"]
    for accessory in punk_accessories:
      punk_attribute_list.append(accessory)
    punk_attribute_list.append(str(len(punk_accessories))+" accessories")
    
    # Create the core dataframe of punk facts
    punk_facts_df = attributes_df[attributes_df['Attribute'].isin(punk_attribute_list)]
    # reset index
    punk_facts_df.reset_index(drop=True, inplace=True)
    # convert the "counts" column to numeric
    punk_facts_df["counts"] = pd.to_numeric(punk_facts_df["counts"])

    # Add rarity scores
    for row in range(len(punk_facts_df)):
      punk_facts_df.at[row,"Rarity %"] = punk_facts_df.at[row,"counts"]/10000 * 100
      punk_facts_df.at[row,"Rarity Score"] = 10000 / punk_facts_df.at[row,"counts"]
      
    # rename the "counts" column
    punk_facts_df.rename(columns = {"counts":"Punks With this Attribute"}, inplace = True)
    
    # remove the index
    punk_facts_df = punk_facts_df.set_index("Attribute")
    
    # Convert the dataframe to html and assign it to a variable
    # Include Bootstrap table formatting
    punk_facts = punk_facts_df.to_html(classes='table table-striped table-hover table-condensed text-center', justify='center')

    # Return the dataframe object to a copy of the index html, and point
    # the variable to the html container name where it will be displayed
    return punk_facts
  

##############################################
# BUILD THE CRYPTO PUNK GRAPHS
##############################################
def buildGraphs (id_selection):


    ########################################
    # IMPORT THE DATA FROM MONGODB ATLAS
    ########################################   
    # 1. construct the connection string for Atlas
    CONNECTION_STRING = "mongodb+srv://"+ user + ":" + password +"@cluster0.wddnt.mongodb.net/crypto_punks_mdb?retryWrites=true&w=majority"
    # 2. Create the connection client to Atlas
    client = pymongo.MongoClient(CONNECTION_STRING) 
    # 3. indicate the database to access in Atlas
    db = pymongo.database.Database(client,'crypto_punks_mdb')
    # 4. assign the connection to the database and collection to a variable (i.e. this still is not 'reading' 
    # the data from the database)
    deals = pymongo.collection.Collection(db, 'txn_history_col')
    punks = pymongo.collection.Collection(db, 'crypto_punks_col')
    # 5. search the database for the unique punk_id value provided as input to 
    # the function and assign the output to a variable. The output will be an object.
    deals_data = json.loads(dumps(deals.find({"punk_id":id_selection})))
    punks_data = json.loads(dumps(punks.find({"punk_id":id_selection})))
    # 6. Convert the json strings to dataframe
    deals_df = pd.DataFrame(deals_data)
    deals_df = deals_df.drop(columns=["_id"])
    # 7. Convert date to datetime
    deals_df['date'] = pd.to_datetime(deals_df['date'])
    # 8. Re-index the dataframe
    deals_df = deals_df.reset_index(drop=True)


    ########################################
    # BUILD THE TYPE PREDICTION IMAGE
    ########################################
    # 1. Get the type prediction
    type_PRED = punks_data[0]["type_PRED"]
    if type_PRED == '0':
        image_name = "male.png"
    elif type_PRED == '1':
        image_name = "female.png"
    else:
        image_name = "other.png"
    # 2. Call the function to Export Chart to AWS
    new_name = "punk_type_PRED.png"
    exportAWS(image_name, new_name)


    ########################################
    # BUILD THE GLASSES PREDICTION IMAGE
    ########################################
    # 1. Get the glasses prediction
    glasses_PRED = punks_data[0]["glasses_PRED"]
    if glasses_PRED == '0':
        image_name = "noglasses.png"
    else:
        image_name = "glasses.png"
    # 2. Call the function to Export Chart to AWS
    new_name = "punk_glasses_PRED.png"
    exportAWS(image_name, new_name)


    ########################################
    # BUILD PRICE HISTORY CHART
    ########################################
    # 1. Filter transaction types
    sold = deals_df[deals_df.txn_type == 'Sold'].groupby("date").agg({"eth": ["median"]}).reset_index("date")
    bid = deals_df[deals_df.txn_type == 'Bid'].groupby("date").agg({"eth": ["median"]}).reset_index("date")
    offered = deals_df[deals_df.txn_type == 'Offered'].groupby("date").agg({"eth": ["median"]}).reset_index("date")
    # 2. Generate plot elements
    plt.figure(figsize=(8,8))
    plt.plot(sold['date'], sold['eth']['median'], label="Sold Median Eth", linewidth=8, color='k')
    plt.plot(bid['date'], bid['eth']['median'], label="Bid Median Eth", linewidth=6, color='g')
    plt.plot(offered['date'], offered['eth']['median'], label="Offered Median Eth", linewidth=4, color='tab:orange')
    plt.legend()
    plt.xticks(rotation=60)
    plt.title("Median Eth Price Over Time for Punk ID")
    # 3. Save the image locally
    image_name = "price_graph.png"
    plt.savefig("static/images/" + image_name)
    # 4. Call the function to Export Chart to AWS
    exportAWS(image_name, image_name)
    

    ########################################
    # BUILD THE TRANSACTION HISTORY CHART
    ########################################
    # 1. Filter the transaction types
    filter_types = ["Sold", "Bid", "Transfer", "Claimed"]
    deals_df = deals_df.loc[deals_df["txn_type"].isin(filter_types)]
    # 2. Sort by dates
    deals_df = deals_df.sort_values(["date"], ascending=True)
    # 3. Re-index the dataframe
    deals_df = deals_df.reset_index(drop=True)
    # 4. Correct dataframe for nan's
    for row in range(len(deals_df)):
        if (deals_df.at[row,"from"] == "nan") & (deals_df.at[row,"txn_type"] == "Claimed"):
            deals_df.at[row,"from"] = "larvalabs"
        if (deals_df.at[row,"to"] == "nan") & (deals_df.at[row,"txn_type"] == "Bid"):
            deals_df.at[row,"to"] = deals_df.at[row-1,"to"]
    # 5. Build graph elements
    plt.figure(figsize=(8,8))
    G = nx.MultiDiGraph()
    # 5.1 Create the network edge labels and nodes
    mylabels={}
    for row in range(len(deals_df)):
        # Add to-from nodes
        G.add_node(deals_df.at[row,"from"])
        # Add edges to the nodes
        G.add_edge(deals_df.at[row,"from"],deals_df.at[row,"to"], color="red", weight=deals_df.at[row,"eth"], size=deals_df.at[row,"eth"])
        # Add the transaction type as edge label
        mylabels[deals_df.at[row,"from"],deals_df.at[row,"to"]]=deals_df.at[row,"txn_type"]
    # 5.2 define the graph type as a circular network
    pos=nx.circular_layout(G)
    # 5.3 Give the node a size based on number of connections (degrees)
    d = dict(G.degree)
    nx.draw(G, pos, node_size = [v**2*200 for v in d.values()], node_color='turquoise', edge_color="cornflowerblue", arrowsize=20, width=3, with_labels=True, font_weight='bold')
    nx.draw_networkx_edge_labels(G, pos, mylabels, label_pos=.5)
    # 6. Save the image locally
    image_name = "network_graph.png"
    plt.savefig("static/images/" + image_name)
    # 7. Call the function to Export Chart to AWS
    exportAWS(image_name, image_name)


    ########################################
    # BUILD THE CRYPYO PUNK IMAGE
    ########################################
    # 1. Obtain the image bitmap
    image_bitmap = punks_data[0]["image_bitmap"]
    # 2. Build the image from the bitmap
    plt.figure(figsize=(7,8))
    img = plt.imshow(image_bitmap)
    # 3. Remove axes tick and tickmarks
    ax = plt.gca()
    ax.axes.xaxis.set_ticks([])
    ax.axes.yaxis.set_ticks([])
    # 4. Add a title
    plt.title("Crypto Punk "+str(id_selection), fontsize=40)
    # 5. Add description of features
    punk_type = punks_data[0]["type"]
    punk_accessories = str(punks_data[0]["accessories"])
    wrapped_label = punk_type+"\n"+("\n".join(wrap(punk_accessories,30)))
    plt.xlabel(wrapped_label, fontsize=25)
    # 6. Save the image locally
    image_name = "crypto_punk.png"
    plt.savefig("static/images/" + image_name)
    # 7. Call the function to Export Chart to AWS
    exportAWS(image_name, image_name)


    return



#########################################################################################
# EXPORT TO AWS S3 BUCKET
#########################################################################################

def exportAWS (image_name, new_name):

    # Create AWS connection
    s3 = boto3.resource('s3', aws_access_key_id=key_id, aws_secret_access_key=secret_access_key)

    # Provide S3 bucket name
    bucket = "cryptopunksbucket"

    # upload image to aws s3
    # warning, the ACL here is set to public-read
    img_data = open("static/images/" + image_name, "rb")
    s3.Bucket(bucket).put_object(Key=new_name, Body=img_data, ContentType="image/png", ACL="public-read")

    return




#########################################################################################
# BUILD OUR MAIN WEB PAGE
#########################################################################################

# Create the Flask instance
app = Flask(__name__)

# Create the visualization homepage
@app.route("/")
def index():
    pagetitle = "HomePage"

    # Generate a random PunK ID
    id_selection = str(random.randrange(0,10000,1))

    # Call the function that builds the graphs
    buildGraphs (id_selection)

    # Call de function that builds the Punk Facts datafrane
    punk_facts = punkFacts(id_selection)

    return render_template("index.html", punk_facts=punk_facts)



if __name__ == '__main__':
    app.run(port=8000)

