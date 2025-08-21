from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
import asyncio
import json
from datetime import datetime, timedelta
import sys
import os

# Ensure project root on sys.path so that 'backend' package can be imported when running from api/
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from backend.data_collector import DataCollector
from backend.query_system import QuerySystem
from backend.system_monitor import SystemMonitor

app = FastAPI(
    title="VPN Monitoring System API",
    description="Backend API for VPN monitoring and system analysis",
    version="1.0.0"
)

# CORS middleware (allow all for development/LAN access)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
data_collector = None
query_system = None
system_monitor = None
monitoring_active = False
continuous_task = None
_last_collection_at = None

# Configurable interval (seconds). Default 15s for faster feedback
COLLECTION_INTERVAL_SECONDS = int(os.getenv("COLLECTION_INTERVAL_SECONDS", "15"))

# Pydantic models
class QueryRequest(BaseModel):
    question: str

class MonitoringStatus(BaseModel):
    active: bool
    last_collection: str | None = None
    next_collection: str | None = None

@app.on_event("startup")
async def startup_event():
    global data_collector, system_monitor, monitoring_active, _last_collection_at, continuous_task
    
    try:
        # Initialize components
        data_collector = DataCollector()
        system_monitor = SystemMonitor()
        
        # Create Elasticsearch indices
        await data_collector.create_indices()

        # Immediate initial collection for fast UI
        try:
            system_data = system_monitor.get_complete_system_info(include_processes=False)
            web_data = data_collector.collect_web_data(include_speed_test=False)
            combined_data = data_collector.collect_all_data(include_processes=False, include_speed_test=False)
            await data_collector.save_system_data(system_data)
            await data_collector.save_web_data(web_data)
            await data_collector.save_combined_data(combined_data)
            _last_collection_at = datetime.now()
            print("✅ İlk veri toplama tamamlandı")
        except Exception as e:
            print(f"⚠️ İlk veri toplama hatası: {e}")
        
        # Start continuous monitoring
        monitoring_active = True
        continuous_task = asyncio.create_task(start_continuous_monitoring())
        
        print("✅ API başlatıldı ve Elasticsearch bağlantısı kuruldu")
        print(f"✅ Sürekli veri toplama başlatıldı (her {COLLECTION_INTERVAL_SECONDS} sn)")
        
    except Exception as e:
        print(f"❌ Başlatma hatası: {e}")

async def start_continuous_monitoring():
    """Sürekli veri toplama: sistem + web + birleşik"""
    global monitoring_active, _last_collection_at
    
    while monitoring_active:
        try:
            if data_collector and system_monitor:
                # Collect real data
                system_data = system_monitor.get_complete_system_info(include_processes=False)
                web_data = data_collector.collect_web_data(include_speed_test=False)
                combined_data = data_collector.collect_all_data(include_processes=False, include_speed_test=False)
                
                # Save to Elasticsearch (separate + combined)
                await data_collector.save_system_data(system_data)
                await data_collector.save_web_data(web_data)
                await data_collector.save_combined_data(combined_data)
                
                _last_collection_at = datetime.now()
                print(f"✅ Veri toplandı: {_last_collection_at.strftime('%H:%M:%S')}")
            
        except Exception as e:
            print(f"❌ Veri toplama hatası: {e}")
        
        # Wait configured interval
        await asyncio.sleep(COLLECTION_INTERVAL_SECONDS)

@app.get("/")
async def root():
    return {
        "message": "VPN Monitoring System API",
        "version": "1.0.0",
        "status": "running",
        "continuous_monitoring": monitoring_active
    }

@app.get("/api/health")
async def health_check():
    try:
        if data_collector:
            health = await data_collector.check_elasticsearch_health()
            return {
                "status": "healthy" if health else "unhealthy",
                "elasticsearch": health,
                "timestamp": datetime.now().isoformat()
            }
        return {"status": "error", "message": "Data collector not initialized"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/status")
async def get_status():
    global monitoring_active, _last_collection_at
    now = datetime.now()
    next_collection_dt = now + timedelta(seconds=COLLECTION_INTERVAL_SECONDS)
    return MonitoringStatus(
        active=monitoring_active,
        last_collection=_last_collection_at.strftime("%H:%M:%S") if _last_collection_at else None,
        next_collection=next_collection_dt.strftime("%H:%M:%S")
    )

@app.post("/api/collect-data")
async def collect_data(background_tasks: BackgroundTasks):
    background_tasks.add_task(collect_data_task)
    return {"message": "Veri toplama başlatıldı"}

async def collect_data_task():
    global _last_collection_at
    try:
        if data_collector and system_monitor:
            system_data = system_monitor.get_complete_system_info(include_processes=True)
            web_data = data_collector.collect_web_data(include_speed_test=True)
            combined_data = data_collector.collect_all_data(include_processes=True, include_speed_test=True)
            await data_collector.save_system_data(system_data)
            await data_collector.save_web_data(web_data)
            await data_collector.save_combined_data(combined_data)
            _last_collection_at = datetime.now()
            print("✅ Manuel veri toplama tamamlandı")
    except Exception as e:
        print(f"❌ Manuel veri toplama hatası: {e}")

@app.post("/api/query")
async def query_system_endpoint(request: QueryRequest):
    global query_system
    try:
        if query_system is None:
            query_system = QuerySystem()
        response = await query_system.query(request.question)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/system-info")
async def get_system_info():
    try:
        if system_monitor:
            return system_monitor.get_complete_system_info(include_processes=False)
        return {"error": "System monitor not initialized"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/latest-data")
async def get_latest_data():
    try:
        if data_collector:
            data = await data_collector.get_latest_data(limit=200)
            return {"data": data}
        return {"error": "Data collector not initialized"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/start-monitoring")
async def start_monitoring():
    global monitoring_active, continuous_task
    if not monitoring_active:
        monitoring_active = True
        if not continuous_task or continuous_task.done() or continuous_task.cancelled():
            continuous_task = asyncio.create_task(start_continuous_monitoring())
        return {"message": "Sürekli izleme başlatıldı"}
    else:
        return {"message": "İzleme zaten aktif"}

@app.post("/api/stop-monitoring")
async def stop_monitoring():
    global monitoring_active, continuous_task
    if monitoring_active:
        monitoring_active = False
        if continuous_task and not continuous_task.cancelled() and not continuous_task.done():
            continuous_task.cancel()
            try:
                await asyncio.sleep(0)
            except Exception:
                pass
        return {"message": "Sürekli izleme durduruldu"}
    else:
        return {"message": "İzleme zaten durdurulmuş"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
