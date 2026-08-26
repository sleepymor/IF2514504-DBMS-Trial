import uvicorn
from fastapi import FastAPI

from bismillah_mbd.routes import auth, milestones, projects, reports, tasks

app = FastAPI(
    title="Bismillah MBD",
    version="0.0.1",
    description="Task Management System backend demonstrating Database Management concepts.",
)

app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(milestones.router)
app.include_router(tasks.router)
app.include_router(reports.router)


@app.get("/")
def root():
    return {
        "message": "Bismillah MBD",
        "version": "0.0.1",
        "docs": "/docs",
    }


def main() -> None:
    uvicorn.run("bismillah_mbd.main:app", host="127.0.0.1", port=8000)
