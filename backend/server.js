import express from "express";
import cors from "cors";
import axios from "axios";

const app = express();

app.use(cors());
app.use(express.json());

const PORT = process.env.PORT || 3001;

// health check
app.get("/health", (req, res) => {
  res.json({ status: "Node backend running" });
});

app.post("/chat", async (req, res) => {

  try {

    console.log("Incoming request body:", req.body);

    const userMessage = req.body.userInput;

    if (!userMessage) {
      return res.status(400).json({
        response: "Message missing from request"
      });
    }

    const llmUrl = process.env.LLM_API_URL || "http://127.0.0.1:5000/api/chat";
    const pythonResponse = await axios.post(
      llmUrl,
      {
        message: userMessage
      }
    );

    res.json({
      response: pythonResponse.data.response
    });

  } catch (error) {

    console.error(
      "Chat error:",
      error.response?.data || error.message
    );

    res.status(500).json({
      response: "LLM server error"
    });

  }

});

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
