"""
MCP Server Manager - Single entry point to launch all MCP servers.

Usage:
    python server_manager.py

This will start all configured MCP servers (Weather, AQI, LLM) concurrently.
Press Ctrl+C to gracefully shutdown all servers.
"""

import asyncio
import subprocess
import sys
import signal
from pathlib import Path
from utils import load_config, setup_logging

logger = setup_logging(__name__)

class ServerManager:
    """Manages multiple MCP server processes"""
    
    def __init__(self):
        self.processes = []
        self.config = load_config()
        
        # Map server configurations to their script files
        self.servers = [
            (
                self.config['servers']['weather']['name'],
                "1_weather_server.py",
                self.config['servers']['weather']['port']
            ),
            (
                self.config['servers']['aqi']['name'],
                "2_Air_Quality_Index_server.py",
                self.config['servers']['aqi']['port']
            ),
            (
                self.config['servers']['llm']['name'],
                "4_LLM_Inference_server.py",
                self.config['servers']['llm']['port']
            )
        ]
    
    def start_all(self):
        """Start all MCP servers"""
        logger.info("=" * 60)
        logger.info("Starting MCP Agent Server Manager")
        logger.info("=" * 60)
        
        for name, script, port in self.servers:
            script_path = Path(__file__).parent / script
            
            if not script_path.exists():
                logger.error(f"❌ Script not found: {script}")
                continue
            
            # Get host from config
            server_key = None
            if 'weather' in script.lower():
                server_key = 'weather'
            elif 'aqi' in script.lower() or 'air' in script.lower():
                server_key = 'aqi'
            elif 'llm' in script.lower():
                server_key = 'llm'
            
            host = self.config['servers'][server_key]['host'] if server_key else '127.0.0.1'
            
            logger.info(f"🚀 Starting {name}")
            logger.info(f"   Host: {host}")
            logger.info(f"   Port: {port}")
            logger.info(f"   Script: {script}")
            
            try:
                proc = subprocess.Popen(
                    [sys.executable, str(script_path)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                self.processes.append((name, proc, port))
                logger.info(f"   ✓ {name} started (PID: {proc.pid})")
                logger.info(f"   URL: http://{host}:{port}")
            except Exception as e:
                logger.error(f"   ✗ Failed to start {name}: {e}")
        
        logger.info("=" * 60)
        logger.info(f"✅ {len(self.processes)} servers running")
        logger.info("")
        for name, proc, port in self.processes:
            # Determine host for this server
            server_key = None
            if 'Weather' in name:
                server_key = 'weather'
            elif 'AQI' in name or 'Air' in name:
                server_key = 'aqi'
            elif 'LLM' in name:
                server_key = 'llm'
            host = self.config['servers'][server_key]['host'] if server_key else '127.0.0.1'
            logger.info(f"   📡 {name}: http://{host}:{port}")
        logger.info("")
        logger.info("   Press Ctrl+C to stop all servers")
        logger.info("=" * 60)
        logger.info("")
        logger.info("📓 Next Steps:")
        logger.info("   1. Open a NEW terminal window")
        logger.info("   2. Run: uv run jupyter lab")
        logger.info("   3. Open and run: Weather_AQI_MCP_Assistant.ipynb")
        logger.info("")
        logger.info("=" * 60)
    
    def stop_all(self):
        """Stop all running servers"""
        logger.info("\n" + "=" * 60)
        logger.info("🛑 Shutting down all servers...")
        logger.info("=" * 60)
        
        for name, proc, port in self.processes:
            try:
                proc.terminate()
                logger.info(f"  ✓ Stopped {name} (port {port}, PID: {proc.pid})")
            except Exception as e:
                logger.error(f"  ✗ Error stopping {name}: {e}")
        
        # Wait for all processes to terminate
        for name, proc, port in self.processes:
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning(f"  ⚠️  Force killing {name}...")
                proc.kill()
                proc.wait()
        
        logger.info("=" * 60)
        logger.info("✅ All servers stopped")
        logger.info("=" * 60)
    
    def check_health(self):
        """Check if all servers are still running"""
        all_healthy = True
        for name, proc, port in self.processes:
            if proc.poll() is not None:
                logger.error(f"⚠️  {name} (port {port}) has stopped unexpectedly")
                # Log stderr if available
                try:
                    stderr = proc.stderr.read()
                    if stderr:
                        logger.error(f"   Error output: {stderr}")
                except:
                    pass
                all_healthy = False
        return all_healthy

async def main():
    """Main entry point for launching all MCP servers"""
    manager = ServerManager()
    
    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        manager.stop_all()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        manager.start_all()
        
        # Monitor server health every 5 seconds
        while True:
            await asyncio.sleep(5)
            if not manager.check_health():
                logger.error("❌ Server health check failed. Shutting down...")
                break
                
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
    finally:
        manager.stop_all()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n👋 Goodbye!")
