# snap3D 🧊

**图片上传 → AI 3D重建 → 可打印模型**

一套完整可落地的全栈应用：FastAPI + Celery + Redis + PostgreSQL + Three.js 前端。

---

## 技术栈

| 层次 | 技术 |
|------|------|
| 前端 | HTML / CSS / Three.js（静态文件，Nginx托管） |
| API  | Python FastAPI + Uvicorn |
| 任务队列 | Celery + Redis |
| 数据库 | PostgreSQL（SQLAlchemy async） |
| 对象存储 | AWS S3 / MinIO |
| 3D 重建 | Tripo3D API / Meshy API |

---

## License

MIT
