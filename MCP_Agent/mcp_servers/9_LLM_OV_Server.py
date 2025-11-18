from fastmcp import FastMCP
from transformers import pipeline
import openvino_genai as ov_genai
import huggingface_hub as hf_hub
import sys
import os

# Initialize the MCP LLM Server
mcp = FastMCP("LLM-Inference", host="0.0.0.0", port=8002)

# Device detection for Intel GPU support
def detect_best_device():
    """Detect the best available device for OpenVINO inference"""
    try:
        import openvino as ov
        core = ov.Core()
        available_devices = core.available_devices
        print(f"Available OpenVINO devices: {available_devices}")
        
        # Prefer GPU (Intel iGPU/dGPU) if available, fallback to CPU
        if any("GPU" in device for device in available_devices):
            return "GPU"
        else:
            return "CPU"
    except Exception as e:
        print(f"Device detection failed: {e}, using CPU")
        return "CPU"

device = detect_best_device()
# device = "NPU"
print(f"Selected device: {device}")
generator = None
model_type = None

try:
    # Try loading OpenVINO optimized Qwen model first
    model_name = "OpenVINO/qwen2.5-1.5b-instruct-int8-ov"
    model_path = "qwen2.5-1.5b-instruct-int8-ov"
    
    print(f"Attempting to load OpenVINO model: {model_name}")
    print("This may take several minutes for first-time download...")
    
    # Download model if not present
    if not os.path.exists(model_path):
        print(f"Downloading model to {model_path}...")
        hf_hub.snapshot_download(model_name, local_dir=model_path)
    
    print(f"Loading OpenVINO GenAI pipeline on {device}...")
    try:
        generator = ov_genai.LLMPipeline(model_path, device)
        config = ov_genai.GenerationConfig()
        config.max_new_tokens = 300
        print(f"Successfully loaded OpenVINO Qwen model on {device}: {model_name}")
        model_type = "openvino"
    except Exception as device_error:
        if device == "GPU":
            print(f"GPU loading failed: {device_error}")
            print("Falling back to CPU for OpenVINO...")
            generator = ov_genai.LLMPipeline(model_path, "CPU")
            print(f"Successfully loaded OpenVINO Qwen model on CPU: {model_name}")
            model_type = "openvino"
        else:
            raise device_error
    
except Exception as qwen_error:
    print(f"Failed to load OpenVINO Qwen model: {qwen_error}")
    print("Falling back to smaller DistilGPT-2 model...")
    
    try:
        # Fallback to smaller model using transformers
        model_name = "distilgpt2"
        
        generator = pipeline(
            "text-generation",
            model=model_name,
            device=-1,  # CPU only
            max_new_tokens=200,
            do_sample=True,
            temperature=0.7,
            pad_token_id=50256
        )
        
        print(f"Successfully loaded fallback model: {model_name}")
        model_type = "transformers"
        
    except Exception as fallback_error:
        print(f"Failed to load fallback model: {fallback_error}")
        generator = None
        model_type = None



# Updated tool: Accepts comprehensive smart city context
@mcp.tool()
async def safety_guidelines(
    weather_report: str = "",
    aqi_report: str = "",
    traffic_report: str = "",
    alerts_report: str = "",
    livability_report: str = "",
    smart_city_report: str = ""
) -> str:
    """
    Generate personalized outdoor safety and health guidelines
    based on provided smart city context: weather, AQI, traffic, alerts, livability, and more.

    Args:
        weather_report (str): Weather report for the location.
        aqi_report (str): Air Quality Index report.
        traffic_report (str): Traffic hazards and congestion info.
        alerts_report (str): City alerts and notifications.
        livability_report (str): Urban livability and facility info.
        smart_city_report (str): Any additional smart city details.

    Returns:
        str: AI-generated safety advice covering outdoor safety, health risks, precautions, urgent alerts, and recommendations for sensitive groups.
    """
    if generator is None:
        return "The language model could not be initialized. Please check your model path and device setup."

    prompt = f"""
    You are a health and safety assistant. Analyze the following smart city context and provide actionable advice. Each section is separated for clarity:

    === TRAFFIC ===
    {traffic_report}

    === ENERGY ===
    {smart_city_report}

    === LIVABILITY ===
    {livability_report}

    === ALERTS ===
    {alerts_report}

    === WEATHER ===
    {weather_report}

    === AQI ===
    {aqi_report}

    Based on all the above, provide:
    1. Overall safety level
    2. Health risks
    3. Precautions
    4. Special advice for sensitive groups
    5. Any urgent alerts or recommendations
    """

    try:
        if model_type == "openvino":
            generation_config = ov_genai.GenerationConfig()
            generation_config.max_new_tokens = 500
            def streamer(subword):
                print(subword, end="", flush=True)
                sys.stdout.flush()
                return False
            result = generator.generate(prompt, generation_config, streamer)
            return result.strip()
        elif model_type == "transformers":
            output = generator(prompt, max_new_tokens=200, do_sample=True, temperature=0.7, return_full_text=False)
            if not output or len(output) == 0:
                return "Failed to generate safety analysis. The model returned no valid output."
            result = output[0]["generated_text"]
            return result.strip()
        else:
            return "No model available for text generation."
    except Exception as e:
        return f"Model pipeline error: {str(e)}"


if __name__ == "__main__":
    mcp.run("sse")