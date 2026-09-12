from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
import asyncio
from datetime import datetime, timedelta
import os

from data_collector import DataCollector
from query_system import QuerySystem
from system_monitor import SystemMonitor

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
active_server_profile = None

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
    host: str
    port: int
    username: str | None = None
    password: str | None = None

class ServerUpdate(BaseModel):
    name: str = None
    host: str = None
    port: int = None
    username: str = None
    password: str = None

class ModelChangeRequest(BaseModel):
    model_id: str

class ModelSettingsRequest(BaseModel):
    max_new_tokens: int | None = None
    temperature: float | None = None
    top_p: float | None = None
    repetition_penalty: float | None = None
    no_repeat_ngram_size: int | None = None
    max_generation_time: float | None = None

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
                "host": {"type": "ip"},
                "port": {"type": "integer"},
                "username": {"type": "keyword"},
                "password": {"type": "keyword"},
                "status": {"type": "keyword"},
                "created_at": {"type": "date"},
                "updated_at": {"type": "date"},
                "last_seen": {"type": "date"},
                "description": {"type": "text"},
                "category": {"type": "keyword"},
                "location": {"type": "text"},
                "owner": {"type": "text"},
                "tags": {"type": "keyword"},
                "monitoring": {"type": "boolean"}
            }
        }
        
        await data_collector.es_client.create_index("servers-config", server_mapping)
        print("✅ Server indices created")
        
        # Remove automatic default server creation - user will create manually
        
    except Exception as e:
        print(f"⚠️ Server indices creation warning: {e}")

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
async def create_server(server_data: dict):
    """Create a new server configuration"""
    try:
        print(f"🔍 Received server data: {server_data}")
        
        # Create server with frontend structure
        new_server = {
            "id": f"server_{int(datetime.now().timestamp())}",
            "name": server_data.get("name", ""),
            "host": server_data.get("ip", ""),  # Frontend sends 'ip', backend uses 'host'
            "port": server_data.get("port", 22),
            "username": server_data.get("username", ""),
            "password": server_data.get("password", ""),
            "description": server_data.get("description", ""),
            "category": server_data.get("category", "server"),
            "location": server_data.get("location", ""),
            "owner": server_data.get("owner", ""),
            "tags": server_data.get("tags", []),
            "status": "inactive",
            "monitoring": False,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "last_seen": None
        }
        
        print(f"🔍 Prepared server object: {new_server}")
        
        result = await data_collector.es_client.index_document("servers-config", new_server)
        print(f"🔍 Elasticsearch result: {result}")
        
        if result:
            # Create monitoring index for the new server
            monitoring_index = f"server-{new_server['id']}-monitoring"
            monitoring_mapping = {
                "properties": {
                    "collection_timestamp": {"type": "date"},
                    "timestamp": {"type": "date"},  # Add timestamp field for sorting
                    "server_id": {"type": "keyword"},
                    "server_name": {"type": "text"},
                    "server_host": {"type": "ip"},
                    "system_data": {"type": "object"},
                    "web_data": {"type": "object"}
                }
            }
            
            try:
                await data_collector.es_client.create_index(monitoring_index, monitoring_mapping)
                print(f"✅ Created monitoring index: {monitoring_index}")
            except Exception as idx_error:
                print(f"⚠️ Monitoring index creation warning: {idx_error}")
            
            print(f"✅ Server added: {new_server['name']} ({new_server['host']})")
            return {"message": "Server başarıyla eklendi", "server": new_server}
        else:
            print("❌ Elasticsearch returned False")
            raise HTTPException(status_code=500, detail="Server kaydedilemedi")
            
    except Exception as e:
        print(f"❌ Server creation error: {type(e).__name__}: {str(e)}")
        import traceback
        print(f"❌ Full traceback: {traceback.format_exc()}")
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

@app.delete("/api/servers/clear-all")
async def clear_all_servers():
    """Clear all server profiles"""
    try:
        # Get all servers first, then delete individually
        servers = await data_collector.es_client.search_documents("servers-config", limit=1000)
        
        if not servers:
            print("ℹ️ No servers found to delete")
            return {"message": "Silinecek sunucu bulunamadı", "deleted_count": 0}
        
        deleted_count = 0
        seen_ids = set()  # Duplicate ID'leri önlemek için
        
        for server in servers:
            server_id = server.get("id")
            if not server_id or server_id in seen_ids:
                continue
                
            seen_ids.add(server_id)
            
            try:
                # Delete each server document individually
                success = await data_collector.es_client.delete_document("servers-config", server_id)
                if success:
                    deleted_count += 1
                    print(f"✅ Deleted server: {server.get('name', 'Unknown')} ({server_id})")
            except Exception as delete_error:
                print(f"⚠️ Failed to delete server {server_id}: {delete_error}")
        
        # Reset active server profile
        global active_server_profile
        active_server_profile = None
        
        print(f"✅ {deleted_count} server profiles cleared")
        return {"message": f"{deleted_count} sunucu profili temizlendi", "deleted_count": deleted_count}
        
    except Exception as e:
        print(f"❌ Clear servers error: {e}")
        import traceback
        print(f"❌ Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Profil temizleme hatası: {str(e)}")

@app.delete("/api/servers/delete-by-name/{server_name}")
async def delete_servers_by_name(server_name: str):
    """Delete all servers with specific name"""
    try:
        # Find servers with matching name
        query = {"term": {"name": server_name}}
        servers = await data_collector.es_client.search_documents("servers-config", query=query, limit=100)
        
        deleted_count = 0
        for server in servers:
            # Delete the server document
            await data_collector.es_client.delete_document("servers-config", server["id"])
            deleted_count += 1
            print(f"✅ Deleted server: {server['name']} ({server['id']})")
        
        # Reset active server profile if any deleted server was active
        global active_server_profile
        if active_server_profile and active_server_profile.get("name") == server_name:
            active_server_profile = None
            print("✅ Reset active server profile")
        
        return {"message": f"{deleted_count} adet '{server_name}' sunucusu silindi", "deleted_count": deleted_count}
        
    except Exception as e:
        print(f"❌ Delete by name error: {e}")
        raise HTTPException(status_code=500, detail=f"Sunucu silme hatası: {str(e)}")

@app.delete("/api/servers/{server_id}")
async def delete_server(server_id: str):
    """Delete server configuration"""
    try:
        if server_id == "localhost":
            raise HTTPException(status_code=400, detail="Localhost server silinemez")
        
        # Delete server document directly by ID
        result = await data_collector.es_client.delete_document("servers-config", server_id)
        
        if result:
            print(f"✅ Server deleted: {server_id}")
            return {"message": "Server başarıyla silindi"}
        else:
            raise HTTPException(status_code=404, detail="Server bulunamadı")
        
    except Exception as e:
        print(f"❌ Server deletion error: {e}")
        raise HTTPException(status_code=500, detail=f"Server silme hatası: {str(e)}")

@app.post("/api/servers/{server_id}/collect")
async def collect_server_data(server_id: str, background_tasks: BackgroundTasks):
    """Collect data for specific server"""
    try:
        # Get server config - Fix Elasticsearch query format
        query = {"term": {"id": server_id}}
        servers = await data_collector.es_client.search_documents("servers-config", query=query, limit=1)
        
        if not servers:
            raise HTTPException(status_code=404, detail="Server bulunamadı")
        
        server = servers[0]
        background_tasks.add_task(collect_server_data_task, server)
        
        return {"message": f"{server['name']} için veri toplama başlatıldı"}
        
    except Exception as e:
        print(f"❌ Server collect error: {e}")
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
            "server_host": server_config["host"],
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

@app.post("/api/servers/{server_id}/activate")
async def activate_server_profile(server_id: str):
    """Activate server profile for data collection"""
    try:
        # Get server config
        query = {"term": {"id": server_id}}
        servers = await data_collector.es_client.search_documents("servers-config", query=query, limit=1)
        
        if not servers:
            raise HTTPException(status_code=404, detail="Server bulunamadı")
        
        server = servers[0]
        
        # Set this server as active profile
        global active_server_profile
        active_server_profile = server
        
        # Update server status
        server["status"] = "active"
        server["monitoring"] = True
        server["updated_at"] = datetime.now().isoformat()
        server["last_seen"] = datetime.now().isoformat()
        
        # Save updated server config
        await data_collector.es_client.index_document("servers-config", server)
        
        print(f"✅ Activated server profile: {server['name']} ({server['host']})")
        return {"message": f"{server['name']} profili aktifleştirildi", "server": server}
        
    except Exception as e:
        print(f"❌ Profile activation error: {e}")
        raise HTTPException(status_code=500, detail=f"Profil aktifleştirme hatası: {str(e)}")

@app.get("/api/active-server-profile")
async def get_active_server_profile():
    """Get currently active server profile"""
    global active_server_profile
    if active_server_profile:
        return {"active_profile": active_server_profile}
    else:
        return {"active_profile": None}

@app.get("/api/active-profile")
async def get_active_profile():
    """Get active server profile for display"""
    global active_server_profile
    if active_server_profile:
        return {
            "id": active_server_profile["id"],
            "name": active_server_profile["name"],
            "host": active_server_profile["host"],
            "category": active_server_profile.get("category", "server"),
            "location": active_server_profile.get("location", ""),
            "owner": active_server_profile.get("owner", "")
        }
    else:
        return None

# Model Management Endpoints
@app.get("/api/models")
async def get_models():
    """Get available models and system information"""
    global query_system
    try:
        if query_system is None:
            try:
                query_system = QuerySystem()
            except Exception as init_error:
                print(f"⚠️ QuerySystem başlatılamadı: {init_error}")
                # Return basic model info without QuerySystem
                from config import MODEL_CONFIG
                return {
                    "models": MODEL_CONFIG['available_models'],
                    "current_model": None,
                    "system_info": {
                        "cuda_available": False,
                        "torch_threads": 1
                    },
                    "model_settings": MODEL_CONFIG['model_settings'],
                    "error": "Model sistemi başlatılamadı, lütfen yeniden deneyin"
                }
        
        status = query_system.get_model_status()
        return {
            "models": status["available_models"],
            "current_model": status["current_model"],
            "system_info": {
                "cuda_available": status["cuda_available"],
                "torch_threads": status["torch_threads"]
            },
            "model_settings": status["model_settings"]
        }
    except Exception as e:
        print(f"❌ Model bilgileri alınamadı: {e}")
        # Fallback response
        from config import MODEL_CONFIG
        return {
            "models": MODEL_CONFIG['available_models'],
            "current_model": None,
            "system_info": {
                "cuda_available": False,
                "torch_threads": 1
            },
            "model_settings": MODEL_CONFIG['model_settings'],
            "error": f"Model bilgileri alınamadı: {str(e)}"
        }

@app.get("/api/models/current")
async def get_current_model():
    """Get current model information"""
    global query_system
    try:
        if query_system is None:
            return {"current_model": None, "status": "not_initialized"}
        
        status = query_system.get_model_status()
        return {
            "current_model": status["current_model"],
            "model_settings": status["model_settings"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Mevcut model bilgisi alınamadı: {str(e)}")

@app.post("/api/models/change")
async def change_model(request: ModelChangeRequest):
    """Change active model"""
    global query_system
    try:
        if query_system is None:
            query_system = QuerySystem()
        
        success = query_system.change_model(request.model_id)
        if success:
            return {"message": f"Model başarıyla değiştirildi: {request.model_id}", "success": True}
        else:
            raise HTTPException(status_code=400, detail=f"Model değiştirilemedi: {request.model_id}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Model değiştirme hatası: {str(e)}")

@app.get("/api/models/settings")
async def get_model_settings():
    """Get current model generation settings"""
    global query_system
    try:
        if query_system is None:
            return {"model_settings": {}}
        
        status = query_system.get_model_status()
        return {"model_settings": status["model_settings"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Model ayarları alınamadı: {str(e)}")

@app.post("/api/models/settings")
async def update_model_settings(request: ModelSettingsRequest):
    """Update model generation settings"""
    global query_system
    try:
        if query_system is None:
            raise HTTPException(status_code=400, detail="Model henüz başlatılmamış")
        
        # Convert request to dict, excluding None values
        settings = {k: v for k, v in request.dict().items() if v is not None}
        query_system.update_model_settings(settings)
        
        return {"message": "Model ayarları güncellendi", "settings": settings}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Model ayarları güncellenemedi: {str(e)}")

@app.post("/api/models/reload")
async def reload_model():
    """Reload current model"""
    global query_system
    try:
        if query_system is None:
            query_system = QuerySystem()
            return {"message": "Model yeniden başlatıldı", "success": True}
        
        # Get current model info and reload it
        status = query_system.get_model_status()
        current_model = status.get("current_model")
        
        if current_model and current_model.get("id"):
            success = query_system.change_model(current_model["id"])
            if success:
                return {"message": "Model yeniden yüklendi", "success": True}
            else:
                raise HTTPException(status_code=400, detail="Model yeniden yüklenemedi")
        else:
            raise HTTPException(status_code=400, detail="Yeniden yüklenecek model bulunamadı")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Model yeniden yükleme hatası: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
