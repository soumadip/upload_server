import json
import os
import secrets

CONFIG_FILE = 'config.json'

def main():
    print("\n" + "="*55)
    print("   🛠️  Lab Server Configuration Wizard")
    print("="*55)

    # 1. Load existing configuration or set empty fallback
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
    else:
        print("❌ config.json not found. Aborting.")
        return

    # 2. Security Enhancement: Auto-replace the default secret key
    if config.get("secret_key") == "super-secret-persistent-key-change-this":
        config["secret_key"] = secrets.token_hex(32)
        print("🔒 Auto-generated new cryptographic secret_key.")

    print("\n💡 Press [Enter] to keep the current value in brackets.\n")

    # --- EXTENDABLE INPUT HANDLERS ---
    def get_string(prompt_text, key):
        current = config.get(key, "")
        res = input(f"🔹 {prompt_text}\n   [{current}]: ").strip()
        config[key] = res if res else current

    def get_int(prompt_text, key):
        current = config.get(key, 0)
        while True:
            res = input(f"🔹 {prompt_text}\n   [{current}]: ").strip()
            if not res: 
                break
            try: 
                config[key] = int(res)
                break
            except ValueError: 
                print("   ❌ Please enter a valid number.")

    def get_list(prompt_text, key):
        current = config.get(key, [])
        curr_str = ", ".join(current)
        res = input(f"🔹 {prompt_text} (comma-separated)\n   [{curr_str}]: ").strip()
        if res:
            config[key] = [x.strip() for x in res.split(',') if x.strip()]

    # --- CONFIGURATION PROMPTS ---
    get_string("Set the Teacher Dashboard Admin PIN:", "admin_pin")
    get_int("Session Timeout (in seconds):", "session_timeout_seconds")
    get_int("Maximum allowed file upload size (MB):", "max_upload_mb")
    get_list("List valid Departments:", "departments")
    get_list("Allowed IP Prefixes (e.g., 192.168.1., 10.0.):", "allowed_ip_prefixes")
    
    # 3. Save safely with pretty-print formatting
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

    print("\n✅ Configuration saved successfully to config.json!")
    print("="*55 + "\n")

if __name__ == "__main__":
    main()
