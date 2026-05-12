import streamlit as st
import json

# --- Core Algorithm ---
def generate_pallet_pattern(pallet_w, pallet_l, box_w, box_l, box_h, layers, interlocking):
    """
    Calculates 3D coordinates for a simple grid-based palletizing pattern.
    """
    pattern_data = []
    box_id = 1
    
    # Quick validation check to ensure the box can actually fit on the pallet
    if box_w > pallet_w or box_l > pallet_l:
        if box_l > pallet_w or box_w > pallet_l:
            return {"error": "Box dimensions are larger than the pallet."}

    for layer in range(layers):
        # Determine if this specific layer should be rotated for interlocking
        # We rotate on odd-numbered layers (1, 3, 5...) if interlocking is True
        rotate_layer = interlocking and (layer % 2 != 0)
        
        # Set current orientation
        current_w, current_l = box_w, box_l
        is_rotated = False
        
        if rotate_layer:
            # Check if the rotated boxes still fit the pallet. If not, fallback to normal orientation.
            if (pallet_w // box_l) > 0 and (pallet_l // box_w) > 0:
                current_w, current_l = box_l, box_w
                is_rotated = True
                
        # Calculate how many boxes fit in the X and Y directions
        cols = int(pallet_w // current_w)
        rows = int(pallet_l // current_l)
        
        # Calculate the Z-coordinate (height) for this layer
        z_coord = layer * box_h
        
        # Generate the coordinates for each box in this layer
        for row in range(rows):
            for col in range(cols):
                x_coord = col * current_w
                y_coord = row * current_l
                
                pattern_data.append({
                    "box_id": box_id,
                    "layer": layer + 1,
                    "x_coordinate": x_coord,
                    "y_coordinate": y_coord,
                    "z_coordinate": z_coord,
                    "is_rotated_90_deg": is_rotated
                })
                box_id += 1
                
    return pattern_data

# --- Streamlit UI Configuration ---
st.set_page_config(page_title="Palletizing Generator", layout="wide")
st.title("📦 Python Palletizing Pattern Generator")
st.write("Generate a JSON palletizing pattern using a deterministic mathematical algorithm.")

# --- Sidebar Inputs ---
st.sidebar.header("Pallet Dimensions")
pallet_w = st.sidebar.number_input("Pallet Width (mm)", min_value=100, value=800)
pallet_l = st.sidebar.number_input("Pallet Length (mm)", min_value=100, value=1200)

st.sidebar.header("Box Dimensions")
box_w = st.sidebar.number_input("Box Width (mm)", min_value=10, value=200)
box_l = st.sidebar.number_input("Box Length (mm)", min_value=10, value=300)
box_h = st.sidebar.number_input("Box Height (mm)", min_value=10, value=150)

st.sidebar.header("Pattern Configuration")
layers = st.sidebar.number_input("Number of Layers", min_value=1, value=3)
interlocking = st.sidebar.checkbox("Interlocking Layers (Optimize for Stability)", value=True)

# --- Generation Logic ---
if st.button("Generate Pattern JSON", type="primary"):
    with st.spinner("Calculating spatial pattern..."):
        # Call the Python algorithm
        result = generate_pallet_pattern(
            pallet_w, pallet_l, box_w, box_l, box_h, layers, interlocking
        )
        
        if isinstance(result, dict) and "error" in result:
            st.error(result["error"])
        else:
            st.success(f"Pattern generated successfully! Total boxes: {len(result)}")
            
            # Display the JSON in the app
            st.json(result)
            
            # Provide the Download Button
            st.download_button(
                label="Download Pattern as JSON",
                data=json.dumps(result, indent=4),
                file_name="pallet_pattern.json",
                mime="application/json"
            )
