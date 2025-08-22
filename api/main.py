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

# Configurable interval (seconds). Default 120s for 2 minutes
COLLECTION_INTERVAL_SECONDS = int(os.getenv("COLLECTION_INTERVAL_SECONDS", "120"))

# Pydantic models
class QueryRequest(BaseModel):
    question: str

class MonitoringStatus(BaseModel):
    active: bool
    last_collection: str | None = None
    next_collection: str | None = None

class ServerConfig(BaseModel):
    name: str
    ip: str
    description: str = ""
    port: int = 22
    username: str = ""
    password: str = ""

class ServerUpdate(BaseModel):
    name: str = None
    ip: str = None
    description: str = None
    port: int = None
    username: str = None
    password: str = None

@app.on_event("startup")
async def startup_event():
    global data_collector, system_monitor, monitoring_active, _last_collection_at, continuous_task
    
    try:
        # Initialize components
        data_collector = DataCollector()
        system_monitor = SystemMonitor()
        
        # Create Elasticsearch indices
        await data_collector.create_indices()
        await create_server_indices()

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
        
        # Do NOT start continuous monitoring automatically
        monitoring_active = False
        continuous_task = None
        
        print("✅ API başlatıldı ve Elasticsearch bağlantısı kuruldu")
        print(f"ℹ️ Otomatik veri toplama kapalı - Manuel başlatma gerekli (aralık: {COLLECTION_INTERVAL_SECONDS} sn)")
        
    except Exception as e:
        print(f"❌ Başlatma hatası: {e}")

async def create_server_indices():
    """Create server-related Elasticsearch indices"""
    try:
        # Server configurations index
        server_mapping = {
            "properties": {
                "id": {"type": "keyword"},
                "name": {"type": "text"},
                "ip": {"type": "ip"},
                "description": {"type": "text"},
                "port": {"type": "integer"},
                "username": {"type": "keyword"},
                "password": {"type": "keyword"},
                "status": {"type": "keyword"},
                "created_at": {"type": "date"},
                "updated_at": {"type": "date"},
                "last_seen": {"type": "date"}
            }
        }
        
        await data_collector.es_client.create_index("servers-config", server_mapping)
        print("✅ Server indices created")
        
        # Add default localhost server if not exists
        await ensure_default_server()
        
    except Exception as e:
        print(f"⚠️ Server indices creation warning: {e}")

async def ensure_default_server():
    """Ensure default localhost server exists"""
    try:
        # Check if localhost server exists
        query = {
            "query": {
                "term": {"ip": "127.0.0.1"}
            }
        }
        
        result = await data_collector.es_client.search_documents("servers-config", query=query, limit=1)
        
        if not result:
            # Create default localhost server
            default_server = {
                "id": "localhost",
                "name": "Yerel Bilgisayar",
                "ip": "127.0.0.1",
                "description": "Bu bilgisayar",
                "port": 22,
                "username": "",
                "password": "",
                "status": "active",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "last_seen": datetime.now().isoformat()
            }
            
            await data_collector.es_client.index_document("servers-config", default_server)
            print("✅ Default localhost server created")
            
    except Exception as e:
        print(f"⚠️ Default server creation warning: {e}")

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

@app.post("/api/init-model")
async def init_model():
    global query_system
    try:
        if query_system is None:
            query_system = QuerySystem()
            return {"message": "Model başarıyla başlatıldı", "status": "initialized"}
        else:
            return {"message": "Model zaten başlatılmış", "status": "already_initialized"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Model başlatma hatası: {str(e)}")

@app.get("/api/model-status")
async def get_model_status():
    global query_system
    return {
        "initialized": query_system is not None,
        "status": "ready" if query_system is not None else "not_initialized"
    }

@app.post("/api/query")
async def query_system_endpoint(request: QueryRequest):
    global query_system
    try:
        if query_system is None:
            raise HTTPException(status_code=400, detail="Model henüz başlatılmamış. Lütfen önce modeli başlatın.")
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

# Server Management Endpoints
@app.get("/api/servers")
async def get_servers():
    """Get all configured servers"""
    try:
        servers = await data_collector.es_client.search_documents("servers-config", limit=100)
        return {"servers": servers}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server listesi alınamadı: {str(e)}")

@app.post("/api/servers")
async def create_server(server: ServerConfig):
    """Create a new server configuration"""
    try:
        server_data = {
            "id": f"server_{int(datetime.now().timestamp())}",
            "name": server.name,
            "ip": server.ip,
            "description": server.description,
            "port": server.port,
            "username": server.username,
            "password": server.password,
            "status": "unknown",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "last_seen": None
        }
        
        result = await data_collector.es_client.index_document("servers-config", server_data)
        if result:
            return {"message": "Server başarıyla eklendi", "server": server_data}
        else:
            raise HTTPException(status_code=500, detail="Server kaydedilemedi")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server ekleme hatası: {str(e)}")

@app.put("/api/servers/{server_id}")
async def update_server(server_id: str, server: ServerUpdate):
    """Update server configuration"""
    try:
        # Get existing server
        query = {"query": {"term": {"id": server_id}}}
        existing = await data_collector.es_client.search_documents("servers-config", query=query, limit=1)
        
        if not existing:
            raise HTTPException(status_code=404, detail="Server bulunamadı")
        
        # Update fields
        server_data = existing[0]
        update_data = server.dict(exclude_unset=True)
        server_data.update(update_data)
        server_data["updated_at"] = datetime.now().isoformat()
        
        result = await data_collector.es_client.index_document("servers-config", server_data)
        if result:
            return {"message": "Server başarıyla güncellendi", "server": server_data}
        else:
            raise HTTPException(status_code=500, detail="Server güncellenemedi")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server güncelleme hatası: {str(e)}")

@app.delete("/api/servers/{server_id}")
async def delete_server(server_id: str):
    """Delete server configuration"""
    try:
        if server_id == "localhost":
            raise HTTPException(status_code=400, detail="Localhost server silinemez")
        
        # Delete server document
        query = {"query": {"term": {"id": server_id}}}
        result = await data_collector.es_client.delete_by_query("servers-config", query)
        
        return {"message": "Server başarıyla silindi"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server silme hatası: {str(e)}")

@app.post("/api/servers/{server_id}/collect")
async def collect_server_data(server_id: str, background_tasks: BackgroundTasks):
    """Collect data for specific server"""
    try:
        # Get server config
        query = {"query": {"term": {"id": server_id}}}
        servers = await data_collector.es_client.search_documents("servers-config", query=query, limit=1)
        
        if not servers:
            raise HTTPException(status_code=404, detail="Server bulunamadı")
        
        server = servers[0]
        background_tasks.add_task(collect_server_data_task, server)
        
        return {"message": f"{server['name']} için veri toplama başlatıldı"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Veri toplama hatası: {str(e)}")

async def collect_server_data_task(server_config):
    """Background task to collect data for specific server"""
    try:
        server_id = server_config["id"]
        
        # Always collect local data regardless of server IP
        # This allows collecting local computer data for any configured server
        system_data = system_monitor.get_complete_system_info(include_processes=True)
        web_data = data_collector.collect_web_data(include_speed_test=True)
        
        # Add server info to data
        system_data["server_id"] = server_id
        system_data["server_name"] = server_config["name"]
        web_data["server_id"] = server_id
        web_data["server_name"] = server_config["name"]
        
        combined_data = {
            "collection_timestamp": datetime.now().isoformat(),
            "server_id": server_id,
            "server_name": server_config["name"],
            "server_ip": server_config["ip"],
            "system_data": system_data,
            "web_data": web_data
        }
        
        # Save to server-specific index
        index_name = f"server-{server_id}-monitoring"
        await data_collector.es_client.index_document(index_name, combined_data)
        
        # Update server last_seen
        server_config["last_seen"] = datetime.now().isoformat()
        server_config["status"] = "active"
        await data_collector.es_client.index_document("servers-config", server_config)
        
        print(f"✅ {server_config['name']} için veri toplandı (yerel bilgisayardan)")
            
    except Exception as e:
        print(f"❌ Server data collection error: {e}")

@app.get("/api/servers/{server_id}/data")
async def get_server_data(server_id: str, limit: int = 100):
    """Get latest data for specific server"""
    try:
        index_name = f"server-{server_id}-monitoring"
        data = await data_collector.es_client.search_documents(index_name, limit=limit)
        return {"data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server verisi alınamadı: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
