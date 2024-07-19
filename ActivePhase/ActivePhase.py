import chromadb
from openai import OpenAI
import os
import subprocess
import time
import threading

# Ensure the OpenAI API key is set
api_key = os.getenv("OPENAI_API_KEY")

# Initialize the OpenAI client with the custom API endpoint
client = OpenAI()

# Function to display ASCII art
def cuddles_art():
    art = """
 ██████ ██    ██ ██████  ██████  ██      ███████ ███████     
██      ██    ██ ██   ██ ██   ██ ██      ██      ██          
██      ██    ██ ██   ██ ██   ██ ██      █████   ███████     
██      ██    ██ ██   ██ ██   ██ ██      ██           ██     
 ██████  ██████  ██████  ██████  ███████ ███████ ███████     
                                                             
                                                                                            
"""
    return art

# Function to connect to ChromaDB and retrieve collection data
def get_chromadb_data(collection_name):
    chromadb_client = chromadb.PersistentClient(path="./data")
    collection = chromadb_client.get_or_create_collection(name=collection_name.lower().replace(' ', '_'))
    # Fetching all documents from the collection
    documents = collection.get(ids=None)
    return collection, documents['documents']

# Function to parse nmap results for open ports
def parse_nmap_results(scan_results):
    open_ports = []
    for line in scan_results.split('\n'):
        if '/tcp' in line and 'open' in line:
            port = line.split('/')[0].strip()
            open_ports.append(int(port))
    return open_ports

# Function to send data to OpenAI and get a decision on which tool to run
def get_tool_decision(scan_results, tools):
    prompt = f"""
    Based on the following nmap scan results and the available tools, decide which tool is most appropriate to run:

    Nmap Scan Results:
    {scan_results}

    Available Tools:
    {tools}

    Please respond with just the name of the appropriate tool to run, and only the filename.
    """
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1000
    )
    print(response)  # Debugging: Print the response to check its structure
    decision = response.choices[0].message.content.strip()
    return decision

# Function to run the selected tool
def run_tool(tool):
    tool_path = os.path.join('./tools', tool)
    if os.path.isfile(tool_path):
        print(f"Running tool: python3 {tool_path}")
        # Running the tool and allowing output to be printed in real-time
        result = subprocess.run(f"python3 {tool_path}", shell=True)
        if result.returncode != 0:
            print(f"Tool {tool} exited with errors.")
    else:
        print(f"Tool {tool} not found in the ./tools directory.")

def main():
    print(cuddles_art())
    print("Starting the process to retrieve information and run nmap scan.")

    # Stage One: Connect to ChromaDB and retrieve data
    org_name = input("Please enter the organisation name to retrieve data: ")
    if not org_name:
        print("Organisation name is required. Exiting.")
        return

    collection, documents = get_chromadb_data(org_name)
    if not documents:
        print(f"No data found for organisation '{org_name}'. Exiting.")
        return

    # Debugging: Print fetched documents to check their structure
    print("Fetched documents:", documents)

    # Extract nmap results from documents
    scan_results = ""
    for doc in documents:
        print("Document text:", doc)  # Debugging: Print each document text
        if 'Scan Results:' in doc:
            scan_results = doc.split('Scan Results:\n')[-1]

    if not scan_results:
        print(f"No scan results found for organisation '{org_name}'. Exiting.")
        return

    # Get a list of available tools
    tools = os.listdir('./tools')
    print(f"Available tools: {tools}")

    # Get the decision from the LLM on which tool to run
    decision = get_tool_decision(scan_results, tools)
    print(f"LLM decision: {decision}")

    # Extract the tool name from the decision
    tool_name = decision.split('\n')[0].strip('`')
    print(f"Selected tool: {tool_name}")

    # Run the selected tool
    run_tool(tool_name)

if __name__ == "__main__":
    main()