import os
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import smtplib
from email.message import EmailMessage

from database import create_document, get_documents
from schemas import UnlockRequest

app = FastAPI(title="Phone Unlock Service API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Phone Unlock Service Backend Running"}

@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}

@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    
    try:
        from database import db
        
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
            
    except ImportError:
        response["database"] = "❌ Database module not found (run enable-database first)"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    
    import os
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    
    return response

# Email helpers

def _send_email_smtp(subject: str, to_email: str, html_body: str, text_body: Optional[str] = None):
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASS")
    from_email = os.getenv("FROM_EMAIL", user or "no-reply@phonelockremover.com")

    if not host or not user or not password:
        # Graceful no-op if SMTP not configured
        print("[email] SMTP not configured. Skipping send.")
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to_email
    if text_body:
        msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")

    with smtplib.SMTP(host, port) as server:
        server.starttls()
        server.login(user, password)
        server.send_message(msg)
        print(f"[email] Sent to {to_email}")


def send_admin_notification(req: UnlockRequest, doc_id: str):
    to_email = os.getenv("ADMIN_EMAIL", "process@phonelockremover.com")
    subject = f"New Unlock Request • {req.brand} {req.model} • {doc_id}"
    html = f"""
    <h2>New Unlock Request</h2>
    <p><strong>Reference ID:</strong> {doc_id}</p>
    <ul>
      <li><strong>Brand:</strong> {req.brand}</li>
      <li><strong>Model:</strong> {req.model}</li>
      <li><strong>Issue:</strong> {req.issue}</li>
      <li><strong>IMEI/Serial:</strong> {req.imei}</li>
      <li><strong>Region/Carrier:</strong> {req.region or '-'}
      <li><strong>Name:</strong> {req.name}</li>
      <li><strong>Email:</strong> {req.email}</li>
      <li><strong>Notes:</strong> {req.notes or '-'}
    </ul>
    <p>Status: {req.status}</p>
    """
    text = (
        f"New Unlock Request\n"
        f"ID: {doc_id}\n"
        f"Brand: {req.brand}\nModel: {req.model}\nIssue: {req.issue}\n"
        f"IMEI/Serial: {req.imei}\nRegion: {req.region or '-'}\n"
        f"Name: {req.name}\nEmail: {req.email}\nNotes: {req.notes or '-'}\n"
        f"Status: {req.status}\n"
    )
    _send_email_smtp(subject, to_email, html, text)


def send_customer_autoresponse(req: UnlockRequest, doc_id: str):
    subject = "We received your unlock request"
    html = f"""
    <h2>Thanks, {req.name}!</h2>
    <p>We've received your request and will get back to you shortly.</p>
    <p><strong>Reference ID:</strong> {doc_id}</p>
    <p>Summary:</p>
    <ul>
      <li><strong>Device:</strong> {req.brand} {req.model}</li>
      <li><strong>Issue:</strong> {req.issue}</li>
      <li><strong>IMEI/Serial:</strong> {req.imei}</li>
      <li><strong>Region/Carrier:</strong> {req.region or '-'}
    </ul>
    <p>If anything is incorrect, reply to this email with corrections.</p>
    <p>— PhoneLockRemover</p>
    """
    text = (
        f"Thanks, {req.name}! We received your unlock request.\n"
        f"Reference ID: {doc_id}\n"
        f"Device: {req.brand} {req.model}\nIssue: {req.issue}\nIMEI/Serial: {req.imei}\nRegion/Carrier: {req.region or '-'}\n"
        f"We'll contact you at this email once we review.\n"
    )
    _send_email_smtp(subject, req.email, html, text)


# API models for responses
class UnlockResponse(BaseModel):
    id: str
    message: str

@app.post("/api/unlock", response_model=UnlockResponse)
def submit_unlock_request(payload: UnlockRequest, background_tasks: BackgroundTasks):
    try:
        doc_id = create_document("unlockrequest", payload)
        # Fire-and-forget email notifications
        background_tasks.add_task(send_admin_notification, payload, doc_id)
        background_tasks.add_task(send_customer_autoresponse, payload, doc_id)
        return {"id": doc_id, "message": "Request received. We'll email you with next steps."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/unlock", response_model=List[dict])
def list_unlock_requests(limit: Optional[int] = 50):
    try:
        docs = get_documents("unlockrequest", limit=limit)
        # Convert ObjectId to str if present
        for d in docs:
            if "_id" in d:
                d["_id"] = str(d["_id"])
        return docs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
