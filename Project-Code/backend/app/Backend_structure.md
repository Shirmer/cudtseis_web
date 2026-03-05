```
backend/
  app/
    main.py       # - FastAPI 应用入口
    db.py         # - 数据库连接和会话管理
    models.py     # - 数据模型定义 (包含地震事件模型)
    ingest.py     # - 获取 USGS 数据并写入数据库的逻辑
    settings.py   # - 配置文件
  requirements.txt # - 项目依赖
```

