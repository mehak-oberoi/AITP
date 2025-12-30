import gradio as gr
import pandas as pd
import requests
from supabase import create_client, Client
from PIL import Image
from io import BytesIO

# --- 1. CONFIGURATION & CREDENTIALS ---
SUPABASE_URL = "https://pxjufyutfmfvklakcfxp.supabase.co"
SUPABASE_KEY = "sb_publishable_A-ItptnkgHBRO20lfFHIdg_t_gqX-tz"

# GitHub Assets (Raw URLs)
GITHUB_LOGO_URL = "https://raw.githubusercontent.com/mehak-oberoi/AITP/main/Gemini_Generated_Image_7648ja7648ja7648.png"
GITHUB_CSS_URL = "https://raw.githubusercontent.com/mehak-oberoi/AITP/main/style.css"

# Initialize Supabase Client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 2. ASSET FETCHING ---
def load_assets():
    logo = None
    css = ""
    
    # Fetch Logo
    try:
        response = requests.get(GITHUB_LOGO_URL)
        response.raise_for_status()
        logo = Image.open(BytesIO(response.content))
    except Exception as e:
        print(f"Warning: Could not load logo. {e}")

    # Fetch CSS
    try:
        response = requests.get(GITHUB_CSS_URL)
        response.raise_for_status()
        css = response.text
    except Exception as e:
        print(f"Warning: Could not load CSS. Using fallback. {e}")
        css = """
        body { background-color: #FAF9F6; color: #333; }
        .gr-button { background-color: #C06C5C; color: white; border-radius: 0px; }
        """
    return logo, css

logo_img, custom_css = load_assets()

# --- 3. BACKEND FUNCTIONS ---

def get_product_lookup():
    """Fetches all products to create a lookup dict (ID -> Name)."""
    try:
        response = supabase.table('products').select("*").execute()
        products = response.data
        # Create a dictionary: {item_id: {'name': sweet_name, 'variant': variant_type, 'price': price_per_kg}}
        lookup = {}
        for p in products:
            lookup[p['item_id']] = {
                'name': p['sweet_name'], 
                'variant': p['variant_type'],
                'price': p['price_per_kg']
            }
        return lookup
    except Exception as e:
        print(f"Error fetching products: {e}")
        return {}

def login_and_fetch(phone_number):
    """
    Authenticates user, fetches their name, order history, and trending items.
    """
    if not phone_number:
        return "Please enter a phone number.", pd.DataFrame(), pd.DataFrame()

    # Clean phone number input (ensure string)
    phone_str = str(phone_number).strip()

    # 1. Fetch Customer Name
    try:
        cust_res = supabase.table('customers').select("full_name").eq("phone", phone_str).execute()
        if cust_res.data and len(cust_res.data) > 0:
            full_name = cust_res.data[0]['full_name']
            greeting = f"## Namaste {full_name} ji!"
        else:
            greeting = "## Namaste! (New Customer)"
    except Exception as e:
        return f"Connection Error: {e}", pd.DataFrame(), pd.DataFrame()

    # 2. Prepare Product Lookup (for joining data)
    product_map = get_product_lookup()

    # 3. Fetch Order History
    try:
        # Fetch orders for this phone
        order_res = supabase.table('orders').select("*").eq("cust_phone", phone_str).order('order_date', desc=True).execute()
        orders = order_res.data
        
        history_data = []
        for o in orders:
            pid = o['product_id']
            p_details = product_map.get(pid, {'name': 'Unknown', 'variant': '-'})
            
            history_data.append({
                "Date": o['order_date'],
                "Order ID": o['order_id'],
                "Sweet": p_details['name'],
                "Variant": p_details['variant'],
                "Qty (Kg)": o['qty_kg'],
                "Total (₹)": o['order_value_inr'],
                "Status": o['status']
            })
        
        df_history = pd.DataFrame(history_data)
    except Exception as e:
        print(f"Error fetching history: {e}")
        df_history = pd.DataFrame(columns=["Error fetching history"])

    # 4. Fetch 'Trending' (Simulated by fetching top products)
    try:
        # Just fetching all products for display as 'Trending'
        # In a real scenario, we would aggregate order counts.
        prod_res = supabase.table('products').select("*").limit(10).execute()
        trending_data = []
        for p in prod_res.data:
            trending_data.append({
                "Sweet Name": p['sweet_name'],
                "Variant": p['variant_type'],
                "Price (₹/kg)": p['price_per_kg'],
                "Dietary Info": "Low Gluten" if p.get('is_low_gluten') else "Standard"
            })
        df_trending = pd.DataFrame(trending_data)
    except Exception as e:
        print(f"Error fetching trending: {e}")
        df_trending = pd.DataFrame(columns=["Error fetching trending"])

    return greeting, df_history, df_trending

# --- 4. UI LAYOUT ---

with gr.Blocks(css=custom_css, title="MishTee-Magic") as demo:
    
    # --- HEADER ---
    with gr.Row(elem_classes="header-row"):
        with gr.Column(scale=1): pass # Spacer
        with gr.Column(scale=2, elem_classes="text-center"):
            if logo_img:
                gr.Image(value=logo_img, show_label=False, show_download_button=False, container=False, height=120)
            gr.Markdown("<h3 style='text-align: center; margin-top: 10px; font-style: italic;'>[ Purity and Health ]</h3>")
        with gr.Column(scale=1): pass # Spacer

    gr.Markdown("---") # Minimalist separator

    # --- LOGIN AREA ---
    with gr.Row():
        with gr.Column(scale=1): pass 
        with gr.Column(scale=2):
            phone_input = gr.Textbox(
                label="Registered Phone Number", 
                placeholder="Enter 10-digit number (e.g., 9876543210)",
                max_lines=1
            )
            login_btn = gr.Button("View My Account", variant="primary")
        with gr.Column(scale=1): pass

    # --- RESULTS AREA ---
    
    # Welcome Message
    welcome_msg = gr.Markdown("## Welcome to MishTee-Magic")
    
    # Data Tabs
    with gr.Tabs():
        with gr.TabItem("My Order History"):
            history_table = gr.DataFrame(
                label="Recent Orders",
                interactive=False,
                wrap=True
            )
        
        with gr.TabItem("Trending Today"):
            trending_table = gr.DataFrame(
                label="Our Bestsellers",
                interactive=False
            )

    # --- INTERACTIONS ---
    login_btn.click(
        fn=login_and_fetch,
        inputs=[phone_input],
        outputs=[welcome_msg, history_table, trending_table]
    )

# --- 5. LAUNCH ---
if __name__ == "__main__":
    demo.launch()
