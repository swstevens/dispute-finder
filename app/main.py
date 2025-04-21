from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import app.plumber as plumber
from io import BytesIO

app = FastAPI()
UPLOAD_DIRECTORY = "app/uploads"
os.makedirs(UPLOAD_DIRECTORY, exist_ok=True)
# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins, you can specify specific origins here like ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    # Process the file (e.g., save it, parse it, etc.)
    # For example, just return the file name and content type in the response
    file_content = await file.read()

    # Convert the file content into a BytesIO object to be used by pdfplumber
    pdf_file = BytesIO(file_content)
    print(plumber.parse_pdf(pdf_file))
    return JSONResponse(content=plumber.parse_pdf(pdf_file))
