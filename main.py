@app.post("/generate-story")
async def generate_story(request: StoryRequest):
    generated_pages = []
    generated_urls = []
    locked_style = None

    for i, page in enumerate(request.pages):
        print(f"Generating Page {i+1}...")
        image_url, image_path = engine.generate_page_image(
            page, 
            request.user_face_filename, 
            locked_style,
            primary_pose=page.primary_pose,
            secondary_pose=page.secondary_pose
        )
        if i == 0 and image_path:
            locked_style = engine.analyze_generated_style(image_path)
            
        # FIXED: We pass 'image_path' for the PDF engine and 'url' for the filename logic
        generated_pages.append({
            'image_path': image_path, 
            'url': image_url, 
            'text': page.text
        })
        generated_urls.append(image_url)

    # This now has everything it needs to find the files on Render
    pdf_url = engine.compile_pdf(generated_pages)

    return {"status": "success", "pdf_url": pdf_url, "image_urls": generated_urls}
