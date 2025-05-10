import streamlit as st
import streamlit_survey as ss
import os
import random
from PIL import Image
import pandas as pd
from datetime import datetime

# Initialize the survey with a progress bar
survey = ss.StreamlitSurvey("Deepfake_Image_Survey")

# Initialize session state for survey completion
if 'survey_completed' not in st.session_state:
    st.session_state.survey_completed = False

# Function to save results to Excel
def save_to_excel(results):
    # Create a DataFrame from results
    df = pd.DataFrame(results)
    
    # Add timestamp
    df['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Define Excel file path
    excel_path = "survey_results.xlsx"
    
    # Check if file exists to append or create new
    if os.path.exists(excel_path):
        existing_df = pd.read_excel(excel_path)
        updated_df = pd.concat([existing_df, df], ignore_index=True)
    else:
        updated_df = df
    
    # Save to Excel
    updated_df.to_excel(excel_path, index=False)
    return excel_path

# Define the on_submit function
def mark_survey_completed():
    st.session_state.survey_completed = True

pages = survey.pages(10, progress_bar=True, on_submit=mark_survey_completed)

# App title and description
st.title("Deepfake or Real Game")
st.subheader("""
This game is designed to test whether you can differentiate between a real image and an AI generated image.
The goal is to raise awarenes on the capabilities of AI image generation. Awareness of the capabilities of AI to the
responsible use of AI technology. Deepfake images are sourcefrom [thispersondoesnotexist.com](thispersondoesnotexist.com) using 
the StyleGAN software, or real photographs from the FFHQ dataset of Creative Commons and public domain images. 

""")
st.write(""" 
For each image:
1. First select whether you think it's Real or Deepfake
2. Then adjust the confidence slider for your selection
""")

# Function to load images with proper path handling
def load_images(image_set):
    try:
        set_path = os.path.join("images", image_set)
        if not os.path.exists(set_path):
            st.error(f"Directory not found: {set_path}")
            return []
            
        image_files = [f for f in os.listdir(set_path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        if not image_files:
            st.error(f"No images found in: {set_path}")
            return []
            
        return [Image.open(os.path.join(set_path, img)) for img in image_files]
    except Exception as e:
        st.error(f"Error loading images from {image_set}: {str(e)}")
        return []

# Load image sets
real_images = load_images("real_images")
fake_images = load_images("fake_images")

# Combine all images (alternating real and fake)
all_images = []
for i in range(min(len(real_images), len(fake_images))):
    all_images.append(("real", real_images[i]))
    all_images.append(("fake", fake_images[i]))

# Ensure we have enough images
if len(all_images) < 10:
    st.error(f"Need at least 5 real and 5 fake images to run the survey. Found {len(real_images)} real and {len(fake_images)} fake images.")
    st.stop()

# Shuffle the images
random.shuffle(all_images)

# Store images in session state if not already there
if 'survey_images' not in st.session_state:
    st.session_state.survey_images = all_images[:10]

# Display each image on its own page with selection and confidence slider
with pages:
    if pages.current < len(st.session_state.survey_images):
        img_type, img = st.session_state.survey_images[pages.current]
        
        # Display the image
        st.image(img, use_container_width=True, caption=f"Image {pages.current + 1}")
        
        # Create two columns for the selection and confidence slider
        col1, col2 = st.columns([1, 2])
        
        with col1:
            # Radio button for Real/Deepfake selection
            selection = st.radio(
                "What do you think this image is?",
                ["Real", "Deepfake"],
                key=f"selection_{pages.current}"
            )
            
        with col2:
            # Confidence slider
            confidence = st.slider(
                "How confident are you?",
                min_value=0, max_value=100, value=50,
                help="0 = Not confident at all, 100 = Absolutely confident",
                key=f"confidence_{pages.current}"
            )
        
        # Store both selection and confidence in survey data
        survey.data[f"selection_{pages.current}"] = selection
        survey.data[f"confidence_{pages.current}"] = confidence

# After submission, show results and save to Excel
if st.session_state.get('survey_completed', False):
    st.header("Survey Results")
    
    results = []
    correct_count = 0
    total_images = len(st.session_state.survey_images)
    
    for i, (img_type, img) in enumerate(st.session_state.survey_images):
        user_selection = survey.data.get(f"selection_{i}", "Unknown")
        user_confidence = survey.data.get(f"confidence_{i}", 50)
        actual_type = "Real" if img_type == "real" else "Deepfake"
        is_correct = (user_selection == actual_type)
        
        # Add to results list
        results.append({
            "Image_Number": i+1,
            "User_Selection": user_selection,
            "Confidence": user_confidence,
            "Actual_Type": actual_type,
            "Is_Correct": is_correct,
            "Image_Path": f"images/{'real_images' if img_type == 'real' else 'fake_images'}/{os.path.basename(img.filename)}"
        })
        
        if is_correct:
            correct_count += 1
        
        # Display result for each image
        st.write(f"""
        **Image {i+1}**:
        - Your selection: {user_selection} (Confidence: {user_confidence}/100)
        - Actual: {actual_type}
        - Result: {"✅ Correct" if is_correct else "❌ Incorrect"}
        """)
        st.image(img, width=200)
        st.write("---")
    
    # Save results to Excel
    excel_path = save_to_excel(results)
    
    # Calculate and display overall accuracy
    accuracy = (correct_count / total_images) * 100
    st.subheader("Your Performance")
    st.metric("Overall Accuracy", f"{accuracy:.1f}%")
    st.metric("Correct Guesses", f"{correct_count}/{total_images}")
    
    # Show aggregated results from all participants
    st.subheader("All Participants' Performance")
    
    if os.path.exists(excel_path):
        # Load all results
        all_results = pd.read_excel(excel_path)
        
        # Calculate statistics for all participants
        participant_stats = all_results.groupby('timestamp').agg({
            'Is_Correct': ['sum', 'count', 'mean']
        }).reset_index()
        
        participant_stats.columns = ['Timestamp', 'Correct', 'Total', 'Accuracy']
        participant_stats['Accuracy'] = participant_stats['Accuracy'] * 100
        
        # Format the table
        participant_stats['Timestamp'] = pd.to_datetime(participant_stats['Timestamp'])
        participant_stats = participant_stats.sort_values('Timestamp', ascending=False)
        participant_stats['Accuracy'] = participant_stats['Accuracy'].round(1)
        
        # Display the table
        st.dataframe(
            participant_stats.style.format({
                'Accuracy': '{:.1f}%',
                'Correct': '{:.0f}',
                'Total': '{:.0f}'
            }),
            use_container_width=True
        )
        
        # Show summary statistics
        st.subheader("Summary Statistics Across All Participants")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Participants", len(participant_stats))
        with col2:
            avg_accuracy = participant_stats['Accuracy'].mean()
            st.metric("Average Accuracy", f"{avg_accuracy:.1f}%")
        with col3:
            best_accuracy = participant_stats['Accuracy'].max()
            st.metric("Best Accuracy", f"{best_accuracy:.1f}%")
    
    # Provide download link for results
    with open(excel_path, "rb") as file:
        st.download_button(
            label="Download Full Results as Excel",
            data=file,
            file_name="deepfake_survey_results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )