import os
import chromadb
import subprocess
import threading
import time
import requests
import paramiko
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor, as_completed

# Ensure the OpenAI API key is set
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.")

# Initialize the OpenAI client with the custom API endpoint
try:
    client = OpenAI(api_key=api_key)
except Exception as e:
    raise ConnectionError(f"Failed to initialize OpenAI client: {e}")

# ASCII Art Function
def cuddles_art():
    art = """
 ██████ ██    ██ ██████  ██████  ██      ███████ ███████     
██      ██    ██ ██   ██ ██   ██ ██      ██      ██          
██      ██    ██ ██   ██ ██   ██ ██      █████   ███████     
██      ██    ██ ██   ██ ██   ██ ██           ██     
 ██████  ██████  ██████  ██████  ███████ ███████ ███████     
                                                             
    """
    return art

# Function to get user input
def get_user_input(prompt):
    response = input(prompt)
    return response if response else "Not provided"

# Function to initialize ChromaDB
def initialize_chromadb(client, collection_name):
    collection_name = collection_name.lower().replace(' ', '_')
    try:
        collection = client.get_or_create_collection(name=collection_name)
    except Exception as e:
        raise RuntimeError(f"Failed to initialize ChromaDB collection: {e}")
    return collection

# Function to save data to ChromaDB
def save_to_chromadb(collection, data):
    documents = [f"{key}: {value}" for key, value in data.items() if value != "Not provided"]
    ids = [f"{data.get('Organisation name', 'unknown')}_{i}" for i in range(len(documents))]
    try:
        collection.add(documents=documents, ids=ids)
    except Exception as e:
        raise RuntimeError(f"Failed to save data to ChromaDB: {e}")

# Function to connect to ChromaDB and retrieve collection data
def get_chromadb_data(collection_name):
    try:
        chromadb_client = chromadb.PersistentClient(path="./data")
        collection = chromadb_client.get_or_create_collection(name=collection_name.lower().replace(' ', '_'))
        documents = collection.get(ids=None)
    except Exception as e:
        raise RuntimeError(f"Failed to retrieve ChromaDB data: {e}")
    return collection, documents['documents']

# Function to parse nmap results for open ports
def parse_nmap_results(scan_results):
    open_ports = []
    for line in scan_results.split('\n'):
        if '/tcp' in line and 'open' in line:
            port = line.split('/')[0].strip()
            open_ports.append(int(port))
    return open_ports

# Function to run nmap scan
def run_nmap_scan(command):
    try:
        print("\nRunning nmap command:")
        print(command)
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=300)
        print("\nnmap command stdout:")
        print(result.stdout)
        print("\nnmap command stderr:")
        print(result.stderr)
        if result.returncode != 0:
            print(f"nmap command failed with return code {result.returncode}")
        return result.stdout
    except subprocess.TimeoutExpired:
        print("nmap command timed out")
        return ""
    except Exception as e:
        print(f"nmap command failed with exception: {e}")
        return ""

# Function to save scan results to ChromaDB
def save_scan_results_to_chromadb(collection, org_name, scan_results):
    document_id = f"{org_name.replace(' ', '_').lower()}_scan_{int(time.time())}"
    document_content = f"Organization Name: {org_name}\nScan Results:\n{scan_results}"
    documents = [document_content]
    ids = [document_id]
    try:
        collection.add(documents=documents, ids=ids)
    except Exception as e:
        raise RuntimeError(f"Failed to save scan results to ChromaDB: {e}")

# Function to display progress
def show_progress():
    while True:
        for i in range(1, 4):
            print(f"\rScanning{'.' * i}", end="", flush=True)
            time.sleep(0.5)
        if stop_event.is_set():
            break

# Function to get tool decision from LLM for a specific port
def get_tool_decision_for_port(port, tools):
    prompt = f"""
    Based on the open port {port} detected by nmap, the description of the service running on that port and the available tools, decide which tool is most appropriate to run:

    Open Port:
    {port}

    Available Tools:
    {tools}

    Please respond with just the name of the appropriate tool to run, and only the filename.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000
        )
        decision = response.choices[0].message.content.strip()
    except Exception as e:
        raise RuntimeError(f"Failed to get tool decision from OpenAI: {e}")
    return decision

# Function to run the selected tool
def run_tool(tool, org_name):
    tool_path = os.path.join('./tools', tool)
    if os.path.isfile(tool_path):
        try:
            result = subprocess.run(f"python3 {tool_path} {org_name}", shell=True)
            if result.returncode != 0:
                print(f"Tool {tool} exited with errors.")
        except Exception as e:
            print(f"Failed to run tool {tool}: {e}")
    else:
        print(f"Tool {tool} not found in the ./tools directory.")

# Main function
def main():
    print(cuddles_art())
    print("Welcome to cuddles. Please provide information about the target.")
    print("If you don't have a piece of information simply press return for the next question.")
    print("You must enter an organisation name.")

    # Stage 1: User Intel Request
    questions = {
        "Organisation name": "Please enter the organisation name: ",
        "Known domains and IPs": "Please enter known domains and IPs separated by commas: ",
        "Known email addresses": "Please enter known email addresses separated by commas: ",
        "Known credentials": "Please enter known credentials (e.g., annie94:superpassword) separated by commas: ",
        "Known names of members": "Please enter known names of members: ",
        "Known technologies": "Please enter known technologies being used by the organisation: ",
        "Known repository URLs": "Please enter known repository URLs for git or similar: ",
        "Any other useful information": "Please enter any other known useful information: "
    }

    responses = {}

    for key, question in questions.items():
        responses[key] = get_user_input(question)

    org_name = responses["Organisation name"]

    if org_name == "Not provided":
        print("Organisation name is required. Exiting.")
        return

    try:
        client = chromadb.PersistentClient(path="./data")
        collection = initialize_chromadb(client, org_name)
    except Exception as e:
        print(f"Failed to initialize ChromaDB client: {e}")
        return

    try:
        save_to_chromadb(collection, responses)
        print(f"Information saved to the database under collection '{org_name}'")
    except Exception as e:
        print(f"Failed to save information to the database: {e}")
        return

    print("Starting the process to retrieve information and run nmap scan.")
    try:
        collection, documents = get_chromadb_data(org_name)
        if not documents:
            print(f"No data found for organisation '{org_name}'. Exiting.")
            return
    except Exception as e:
        print(f"Failed to retrieve data from the database: {e}")
        return

    ips_and_domains = []
    for doc in documents:
        if 'Known domains and IPs' in doc:
            ips_and_domains_str = doc.split('Known domains and IPs: ')[-1]
            ips_and_domains.extend(ips_and_domains_str.split(','))

    if not ips_and_domains:
        print(f"No IP addresses or domains found for organisation '{org_name}'. Exiting.")
        return

    shallow_scan_command = f"nmap {' '.join(ips_and_domains)} -sV -sC"
    global stop_event
    stop_event = threading.Event()
    progress_thread = threading.Thread(target=show_progress)
    progress_thread.start()

    scan_result = run_nmap_scan(shallow_scan_command)
    stop_event.set()
    progress_thread.join()

    open_ports = parse_nmap_results(scan_result)
    if not open_ports:
        deep_scan_command = f"nmap {' '.join(ips_and_domains)} -p- -sC -sV"
        print("No open ports found with shallow scan. Performing deeper scan.")
        stop_event = threading.Event()
        progress_thread = threading.Thread(target=show_progress)
        progress_thread.start()

        scan_result = run_nmap_scan(deep_scan_command)
        stop_event.set()
        progress_thread.join()

    print("\nNmap scan results:")
    print(scan_result)
    try:
        save_scan_results_to_chromadb(collection, org_name, scan_result)
    except Exception as e:
        print(f"Failed to save scan results to the database: {e}")
        return

    tools = os.listdir('./tools')
    with ThreadPoolExecutor() as executor:
        futures = []
        for port in open_ports:
            futures.append(executor.submit(get_tool_decision_for_port, port, tools))

        for future in as_completed(futures):
            try:
                tool_name = future.result().split('\n')[0].strip('`')
                print(f"Selected tool for port: {tool_name}")
                run_tool(tool_name, org_name)
            except Exception as e:
                print(f"Failed to select or run tool: {e}")

if __name__ == "__main__":
    main()
