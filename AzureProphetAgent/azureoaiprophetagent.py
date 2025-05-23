import openai
import certifi
import ssl
import os
from dotenv import load_dotenv
import httpx
import pandas as pd
from prophet import Prophet
import matplotlib.pyplot as plt

# Load environment variables
load_dotenv()
az_openai_api_key = os.getenv("AZURE_OPENAI_API_KEY")
az_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")  # e.g. https://<resource>.openai.azure.com/
az_openai_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")  # e.g. gpt-35-turbo
az_openai_api_version = os.getenv("AZURE_OPENAI_API_VERSION")  # e.g. 2023-05-15

# Optional SSL cert fix
openai.ssl_context = ssl.create_default_context(cafile=certifi.where())
http_client = httpx.Client(verify=certifi.where())

# -----------------------------
# LangChain Agent Setup
# -----------------------------
from langchain.agents import initialize_agent, Tool
from langchain.tools import tool
from langchain_openai import AzureChatOpenAI

@tool
def forecast_timeseries(input_str: str) -> str:
    """
    Forecasts time series data using Facebook Prophet.
    Input should be in the format: '<csv_path>, <periods>'
    """
    try:
        csv_path, periods = input_str.split(",")
        csv_path = csv_path.strip()
        periods = int(periods.strip())
    except Exception:
        return "Error: Input format must be '<csv_path>, <periods>'"

    df = pd.read_csv(csv_path)
    model = Prophet()
    model.fit(df)

    future = model.make_future_dataframe(periods=periods)
    forecast = model.predict(future)

    forecast[['ds', 'yhat']].tail(periods).to_csv("forecast_output.csv", index=False)
    return "Forecast complete. See forecast_output.csv for results."

@tool
def plot_forecast(csv_path: str) -> str:
    """
    Plots a forecast CSV generated by Prophet.
    """
    forecast_df = pd.read_csv(csv_path)
    forecast_df.plot(x="ds", y="yhat", title="Forecast")
    plt.savefig("forecast_plot.png")
    return "Plot saved as forecast_plot.png"

# Define tools
tools = [forecast_timeseries, plot_forecast]

# Use AzureChatOpenAI
llm = AzureChatOpenAI(
    azure_deployment=az_openai_deployment,
    openai_api_key=az_openai_api_key,
    azure_endpoint=az_openai_endpoint,
    openai_api_version=az_openai_api_version,
    temperature=0,
    http_client=http_client  # to handle SSL certs
)

# Initialize the agent
agent = initialize_agent(tools, llm, agent="zero-shot-react-description", verbose=True)

# Run the agent
agent.run("Use 'forecast_timeseries' on 'sales_data.csv, 30' and then use 'plot_forecast' on 'forecast_output.csv'.")
