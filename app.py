# Parts Transfer Scanner - Version 8 (With Keep-Alive)
# Added auto-refresh keep-alive to prevent sleeping

import streamlit as st
import pandas as pd
from datetime import datetime
import requests
import json
import time

# Configure page
st.set_page_config(
    page_title="Parts Transfer Scanner - v8",
    page_icon="📦",
    layout="centered"
)

# Health check endpoint - accessible at /?health=check
if 'health' in st.query_params and st.query_params['health'] == 'check':
    st.json({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "uptime": time.time()
    })
    st.stop()

# Google Sheets URL
GOOGLE_SHEETS_URL = 'https://script.google.com/macros/s/AKfycbxzaNbIreGkCcjdS4n2u4bLIuQyISaVIPl_va7gX0qLikpsrksdW7Y9SrhsRd9z2jmxXw/exec'

# Initialize session state
if 'parts' not in st.session_state:
    st.session_state.parts = []
if 'transfer_complete' not in st.session_state:
    st.session_state.transfer_complete = False
if 'transfer_in_progress' not in st.session_state:
    st.session_state.transfer_in_progress = False
if 'scanning_mode' not in st.session_state:
    st.session_state.scanning_mode = None
if 'last_scanned_code' not in st.session_state:
    st.session_state.last_scanned_code = ""
if 'last_scan_time' not in st.session_state:
    st.session_state.last_scan_time = 0
if 'scanner_key' not in st.session_state:
    st.session_state.scanner_key = 0
if 'last_processed_code' not in st.session_state:
    st.session_state.last_processed_code = ""
if 'keep_alive_active' not in st.session_state:
    st.session_state.keep_alive_active = True
if 'last_activity' not in st.session_state:
    st.session_state.last_activity = time.time()

# Update last activity timestamp
st.session_state.last_activity = time.time()

# Scan cooldown to prevent rapid duplicate scans
SCAN_COOLDOWN = 1.5  # 1.5 seconds between same codes

def add_part(barcode, from_scanner=False):
    """Add or update part in the list - latest items appear at top"""
    if not barcode or len(barcode.strip()) < 2:
        if from_scanner:
            st.error("Invalid QR code")
        else:
            st.error("Invalid part number")
        return False
    
    barcode = barcode.strip().upper()
    current_time = time.time()
    
    # For scanner: prevent rapid duplicate scans but allow intentional repeats
    if from_scanner:
        if (barcode == st.session_state.last_scanned_code and 
            current_time - st.session_state.last_scan_time < SCAN_COOLDOWN):
            return False  # Too soon, ignore
        
        st.session_state.last_scanned_code = barcode
        st.session_state.last_scan_time = current_time
    
    # Check if part already exists
    existing_part_index = None
    for i, part in enumerate(st.session_state.parts):
        if part['barcode'] == barcode:
            existing_part_index = i
            break
    
    if existing_part_index is not None:
        # Remove existing part and add it to the top with updated quantity
        existing_part = st.session_state.parts.pop(existing_part_index)
        existing_part['quantity'] += 1
        existing_part['timestamp'] = datetime.now()
        st.session_state.parts.insert(0, existing_part)
        
        if from_scanner:
            st.success(f"🎯 Item: {barcode} scanned (Total qty: {existing_part['quantity']})")
        else:
            st.success(f"✅ Updated: {barcode} (qty: {existing_part['quantity']})")
        return True
    
    # Add new part at the top of the list
    st.session_state.parts.insert(0, {
        'barcode': barcode,
        'quantity': 1,
        'timestamp': datetime.now()
    })
    
    if from_scanner:
        st.success(f"🎯 Item: {barcode} scanned (Total qty: 1)")
    else:
        st.success(f"✅ Added: {barcode}")
    return True

def remove_part(index):
    """Remove part from list"""
    if 0 <= index < len(st.session_state.parts):
        removed = st.session_state.parts.pop(index)
        st.success(f"🗑️ Removed: {removed['barcode']}")

def update_quantity(index, new_qty):
    """Update part quantity"""
    if 0 <= index < len(st.session_state.parts) and new_qty > 0:
        st.session_state.parts[index]['quantity'] = new_qty
        st.session_state.parts[index]['timestamp'] = datetime.now()

def save_transfer_data(from_location, to_location, parts_data):
    """Save transfer to Google Sheets"""
    try:
        transfer_data = {
            'timestamp': datetime.now().isoformat(),
            'fromLocation': from_location,
            'toLocation': to_location,
            'parts': parts_data,
            'totalParts': sum(p['quantity'] for p in parts_data),
            'partTypes': len(parts_data)
        }
        
        response = requests.post(
            GOOGLE_SHEETS_URL,
            json=transfer_data,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        return True
    except Exception as e:
        st.error(f"Save failed: {str(e)}")
        return False

def reset_transfer():
    """Reset everything for new transfer"""
    st.session_state.parts = []
    st.session_state.transfer_complete = False
    st.session_state.transfer_in_progress = False
    st.session_state.scanning_mode = None
    st.session_state.last_scanned_code = ""
    st.session_state.last_scan_time = 0
    st.session_state.scanner_key = 0
    st.session_state.last_processed_code = ""

def generate_transfer_id():
    """Generate unique transfer ID"""
    return f"TXN-{datetime.now().strftime('%Y%m%d%H%M%S')}"

def generate_transfer_document(transfer_id, from_location, to_location, parts):
    """Generate printable transfer document"""
    doc_content = f"""PARTS TRANSFER DOCUMENT
======================
Transfer ID: {transfer_id}
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

FROM LOCATION: {from_location}
TO LOCATION: {to_location}

ITEMS TRANSFERRED:
"""
    
    for i, part in enumerate(parts, 1):
        doc_content += f"\n{i:2d}. {part['barcode']} - Qty: {part['quantity']} [ ] Verified"
    
    doc_content += f"\n\nTOTAL ITEMS: {sum(p['quantity'] for p in parts)}"
    doc_content += f"\nTOTAL PART TYPES: {len(parts)}"
    doc_content += "\n\nTRANSFER COMPLETED BY: ________________"
    doc_content += "\nSIGNATURE: ________________  DATE: ________________"
    
    return doc_content

# CSS for better UI
st.markdown("""
<style>
    .main > div {
        padding-top: 1rem;
    }
    .stButton > button {
        width: 100%;
        height: 3rem;
        font-size: 1.2rem;
        font-weight: bold;
    }
    .scanning-section {
        border: 3px solid #2196F3;
        border-radius: 15px;
        padding: 20px;
        margin: 15px 0;
        background-color: #f0f8ff;
    }
    .scanner-active {
        border-color: #ff4444;
        background-color: #fff8f8;
    }
    .mode-selector {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
    }
    input[type="text"] {
        font-size: 16px !important;
    }
    
    /* Disabled button styling */
    .stButton > button:disabled {
        background-color: #cccccc !important;
        color: #666666 !important;
        cursor: not-allowed !important;
        opacity: 0.6 !important;
    }
    
    /* AGGRESSIVE TARGETING OF EMPTY CONTAINERS */
    /* Target all empty divs that could be creating the bars */
    div[data-testid="stVerticalBlock"]:empty,
    div[data-testid="stHorizontalBlock"]:empty,
    div[data-testid="stForm"]:empty,
    div[data-testid="element-container"]:empty,
    .element-container:empty,
    .stVerticalBlock:empty,
    .stHorizontalBlock:empty,
    .stForm:empty {
        display: none !important;
        height: 0 !important;
        min-height: 0 !important;
        padding: 0 !important;
        margin: 0 !important;
        border: none !important;
    }
    
    /* Target containers with only whitespace */
    div[data-testid="stVerticalBlock"]:not(:has(*)),
    div[data-testid="element-container"]:not(:has(*)) {
        display: none !important;
    }
    
    /* Remove any mysterious borders from containers */
    div[style*="border"],
    div[style*="outline"] {
        border: none !important;
        outline: none !important;
    }
    
    /* Nuclear option - hide any div that's creating visual borders but has no meaningful content */
    div:empty:not([data-testid="stChatMessage"]):not([data-testid="stSelectbox"]):not([data-testid="stTextInput"]) {
        display: none !important;
    }
</style>
""", unsafe_allow_html=True)

# Main App
st.title("📦 Parts Transfer")

# MAIN APP INTERFACE

# Transfer Details Section
with st.container():
    col1, col2 = st.columns(2)
    with col1:
        from_location_raw = st.text_input("From Location", placeholder="Type/Scan the location")
        from_location = from_location_raw.strip() if from_location_raw else ""
    with col2:
        to_location_raw = st.text_input("To Location", placeholder="Type/Scan the location")
        to_location = to_location_raw.strip() if to_location_raw else ""

# Input Method Selection
st.header("📱 Add Parts")

with st.container():
    st.markdown('<div class="mode-selector">', unsafe_allow_html=True)
    
    # Mode selection buttons
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📷 QR Scanner", type="primary" if st.session_state.scanning_mode == "qr_scanner" else "secondary"):
            st.session_state.scanning_mode = "qr_scanner"
            st.rerun()
    
    with col2:
        if st.button("⌨️ Manual Entry", type="primary" if st.session_state.scanning_mode == "manual" else "secondary"):
            st.session_state.scanning_mode = "manual"
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

# QR Scanner Section
if st.session_state.scanning_mode == "qr_scanner":
    with st.container():
        st.markdown('<div class="scanning-section scanner-active">', unsafe_allow_html=True)
        
        st.info("📱 **QR Scanner Active** - Continuously scans QR codes")
        
        # Close button FIRST - before scanner renders
        if st.button("❌ Close Scanner", key="close_scanner"):
            st.session_state.scanning_mode = None
            st.session_state.scanner_key += 1
            # Clear any scanner state
            for key in list(st.session_state.keys()):
                if key.startswith('qrcode_scanner'):
                    del st.session_state[key]
            st.rerun()
        
        try:
            from streamlit_qrcode_scanner import qrcode_scanner
            
            # Only render scanner if we're not closing
            if st.session_state.scanning_mode == "qr_scanner":
                scanner_key = f'qrcode_scanner_{st.session_state.scanner_key}'
                qr_code = qrcode_scanner(key=scanner_key)
                
                # Process scanned code only if it's new
                if qr_code and qr_code != st.session_state.last_processed_code:
                    st.session_state.last_processed_code = qr_code
                    if add_part(qr_code, from_scanner=True):
                        st.rerun()
                    
        except ImportError:
            st.error("❌ QR Scanner library not installed. Please install: pip install streamlit-qrcode-scanner")
            st.info("💡 Use Manual Entry mode instead")
        
        st.markdown('</div>', unsafe_allow_html=True)

# Manual Entry Section
elif st.session_state.scanning_mode == "manual":
    with st.container():
        st.markdown('<div class="scanning-section">', unsafe_allow_html=True)
        
        st.info("⌨️ **Manual Entry Mode** - Type part number and press Enter")
        
        # Simple form - the CSS above should hide any borders now
        with st.form(key='manual_form', clear_on_submit=True):
            manual_code = st.text_input(
                "", 
                placeholder="Enter part number",
                label_visibility="collapsed"
            )
            
            # The submit button - form needs this for Enter key to work
            submitted = st.form_submit_button("Add Part", use_container_width=True)
            
            if submitted and manual_code and manual_code.strip():
                if add_part(manual_code.strip(), from_scanner=False):
                    st.rerun()
        
        # Close button outside the form
        if st.button("❌ Close Manual Entry", key="close_manual"):
            st.session_state.scanning_mode = None
            st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)

# Show mode selection hint
if st.session_state.scanning_mode is None:
    st.info("👆 **Choose a method above** to start adding parts")

# Parts List Section
st.header("📋 Parts List")

if st.session_state.parts:
    # Summary
    total_items = sum(p['quantity'] for p in st.session_state.parts)
    st.info(f"📊 **{total_items} total items** • **{len(st.session_state.parts)} different parts**")
    
    # Parts display
    for i, part in enumerate(st.session_state.parts):
        with st.container():
            col1, col2, col3 = st.columns([4, 3, 1])
            
            with col1:
                st.write(f"**{part['barcode']}**")
            
            with col2:
                # Quantity controls - now with manual input
                qty_col1, qty_col2, qty_col3, qty_col4 = st.columns([1, 1, 2, 1])
                
                with qty_col1:
                    if st.button("➖", key=f"dec_{i}", help="Decrease"):
                        if part['quantity'] > 1:
                            update_quantity(i, part['quantity'] - 1)
                            st.rerun()
                
                with qty_col2:
                    if st.button("➕", key=f"inc_{i}", help="Increase"):
                        update_quantity(i, part['quantity'] + 1)
                        st.rerun()
                
                with qty_col3:
                    # Manual quantity input
                    new_qty = st.number_input(
                        "",
                        min_value=1,
                        max_value=9999,
                        value=part['quantity'],
                        key=f"qty_input_{i}",
                        label_visibility="collapsed"
                    )
                    
                    # Update quantity if changed
                    if new_qty != part['quantity']:
                        update_quantity(i, new_qty)
                        st.rerun()
                
                with qty_col4:
                    st.write("qty")
            
            with col3:
                if st.button("🗑️", key=f"del_{i}", help="Remove"):
                    remove_part(i)
                    st.rerun()
            
            if i < len(st.session_state.parts) - 1:
                st.divider()
else:
    st.info("No parts added yet - select a method above to start")

# Complete Transfer Section
st.header("✅ Complete Transfer")

can_complete = (
    from_location and 
    to_location and 
    st.session_state.parts and 
    not st.session_state.transfer_complete and
    not st.session_state.transfer_in_progress
)

if can_complete:
    # Show transfer summary before completing
    st.subheader("📋 Transfer Summary")
    
    # Location summary
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"**FROM:** {from_location}")
    with col2:
        st.info(f"**TO:** {to_location}")
    
    # Parts summary
    total_items = sum(p['quantity'] for p in st.session_state.parts)
    st.success(f"📊 **{total_items} total items** • **{len(st.session_state.parts)} different parts**")
    
    # Show parts list
    with st.expander("📦 View all items to transfer", expanded=True):
        for i, part in enumerate(st.session_state.parts, 1):
            st.write(f"{i}. **{part['barcode']}** - Qty: {part['quantity']}")
    
    if st.button("🚀 Complete Transfer", type="primary"):
        # Set transfer in progress to prevent multiple clicks
        st.session_state.transfer_in_progress = True
        st.rerun()

elif st.session_state.transfer_in_progress:
    # Show processing state
    st.info("🔄 **Processing transfer...** Please wait")
    
    # Perform the actual transfer
    parts_data = [{'barcode': p['barcode'], 'quantity': p['quantity']} for p in st.session_state.parts]
    total_items = sum(p['quantity'] for p in st.session_state.parts)
    
    if save_transfer_data(from_location, to_location, parts_data):
        st.success(f"✅ **Transfer Completed!** {total_items} items transferred")
        st.balloons()
        
        # Show completed transfer summary
        st.subheader("🧾 Transfer Receipt")
        st.write(f"**Transfer ID:** TXN-{datetime.now().strftime('%Y%m%d%H%M%S')}")
        st.write(f"**From:** {from_location} **→ To:** {to_location}")
        st.write(f"**Total Items:** {total_items}")
        st.write(f"**Completed:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Auto-reset for new transfer
        reset_transfer()
        st.rerun()
    else:
        # Reset transfer in progress on failure
        st.session_state.transfer_in_progress = False
        st.rerun()

else:
    # Show what's missing or if disabled
    if st.session_state.transfer_in_progress:
        st.info("🔄 **Transfer in progress...** Please wait")
    else:
        missing = []
        if not from_location:
            missing.append("From Location")
        if not to_location:
            missing.append("To Location")
        if not st.session_state.parts:
            missing.append("Add at least one part")
        
        if missing:
            st.warning(f"⚠️ **Required:** {', '.join(missing)}")

# Emergency reset button
if st.session_state.parts:
    st.divider()
    if st.button("🔄 Clear All Parts", help="Emergency reset - clear all parts"):
        reset_transfer()
        st.rerun()
