from fastapi import FastAPI
from bismillah_mbd.routes import projects, task, report, milestones

app = FastAPI(
    title="Bismillah MBD",
    version="0.0.1"
)

app.include_router(projects.router)
app.include_router(milestones.router)
app.include_router(task.router)
app.include_router(report.router)


@app.get("/")
def root():
    return {
        "message": "Bismillah MBD",
        "version": "0.0.1",
    }