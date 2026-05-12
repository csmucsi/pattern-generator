import streamlit as st
import json
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# --- Core Algorithm ---
def generate_pallet_pattern(pallet_w, pallet_l, box_w, box_l, box_h, layers, interlocking):
    """
    Calculates 3D coordinates for a simple grid-based palletizing pattern.
    """
    pattern_data = []
    box_id = 1
    
    if box_w > pallet_w or box_l > pallet_l:
        if box_l > pallet_w or box_w > pallet_l:
            return {"error": "Box dimensions are larger than the pallet."}

    for layer in range(layers):
        rotate_layer = interlocking and (layer % 2 != 0)
        
        current_w, current_l = box_w, box_l
        is_rotated = False
        
        if rotate_layer:
            if (pallet_w // box_l) > 0 and (pallet_l // box_w) > 0:
                current_w, current_l = box_l, box_w
                is_rotated = True
                
        cols = int(pallet_w // current_w)
        rows = int(pallet_l // current_l)
        z_coord = layer * box_h
        
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

# --- Visualization Function ---
def plot_layer(pattern_data, layer_num, pallet_w, pallet_l, box_w, box_l):
    """
    Plots a 2D top-down view of a specific layer using Matplotlib.
    """
    # Create figure and axis
    fig, ax = plt.subplots(figsize=(6, 6 * (pallet_l / pallet_w)))
    
    # Draw the Pallet (Brown base)
    pallet_rect = patches.Rectangle(
        (0, 0), pallet_w, pallet_l, 
        linewidth=2, edgecolor='black', facecolor='#8B4513', alpha=0.3
    )
    ax.add_patch(pallet_rect)
    
    # Filter boxes for the chosen layer
    layer_boxes = [box for box in pattern_data if box['layer'] == layer_num]
    
    # Draw each box
    for box in layer_boxes:
        x = box['x_coordinate']
        y = box['y_coordinate']
        rotated = box['is_rotated_90_deg']
        
        # Determine the visual width and length based on rotation
        draw_w = box_l if rotated else box_w
        draw_l = box_w if rotated else box_l
        
        # Create the box rectangle (Blue)
        box_rect = patches.Rectangle(
            (x, y), draw_w, draw_l, 
            linewidth=1.5, edgecolor='black', facecolor='#4682B4', alpha=0.8
        )
        ax.add_patch(box_rect)
        
        # Add the Box ID text in the center of the box
        ax.text(x + draw_w/2, y + draw_l/2, str(box['box_id']), 
                color='white', ha='center', va='center', fontweight='bold')

    # Set axis properties
    ax.set_xlim(-50, pallet_w + 50)
    ax.set_ylim(-50, pallet_l + 50)
    ax.set_aspect('equal') # Ensures squares look like squares, not stretched rectangles
    ax.set_title(f"Layer {layer_num} Top-Down View")
    ax.set_xlabel("Width (mm)")
    ax.set_ylabel("Length (mm)")
    
    return fig

# --- Streamlit UI Configuration ---
st.set_page_config(page_title="Palletizing Generator", layout="wide")
st.title("📦 Python Palletizing Pattern Generator")
st.write("Generate and visualize a palletizing pattern.")

# Initialize session state to store our generated pattern
if 'pattern_data' not in st.session_state:
    st.session_state.pattern_data = None

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

# --- Generation Trigger ---
if st.sidebar.button("Generate Pattern", type="primary"):
    with st.spinner("Calculating spatial pattern..."):
        result = generate_pallet_pattern(
            pallet_w, pallet_l, box_w, box_l, box_h, layers, interlocking
        )
        # Save the result to session state so it persists during dropdown changes
        st.session_state.pattern_data = result

# --- Display Logic ---
if st.session_state.pattern_data:
    pattern_data = st.session_state.pattern_data
    
    if isinstance(pattern_data, dict) and "error" in pattern_data:
        st.error(pattern_data["error"])
    else:
        st.success(f"Pattern generated successfully! Total boxes: {len(pattern_data)}")
        
        # Create two columns: Left for visualization, Right for JSON/Download
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("Visual Layout")
            # Drop-down to select the layer
            selected_layer = st.selectbox(
                "Select Layer to View", 
                options=list(range(1, layers + 1))
            )
            
            # Generate and display the plot
            fig = plot_layer(pattern_data, selected_layer, pallet_w, pallet_l, box_w, box_l)
            st.pyplot(fig)
            
        with col2:
            st.subheader("JSON Output")
            # Provide the Download Button
            st.download_button(
                label="Download Pattern as JSON",
                data=json.dumps(pattern_data, indent=4),
                file_name="pallet_pattern.json",
                mime="application/json"
            )
            
            # Display the JSON inside an expander to keep the UI clean
            with st.expander("View JSON Data"):
                st.json(pattern_data)
                
