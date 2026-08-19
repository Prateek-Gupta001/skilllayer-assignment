package main

import (
	"fmt"
	"os"
	"time"
)

const logFile = "PROMPT_LOG.md"

func LogInteraction(role string, content string) {
	f, err := os.OpenFile(logFile, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		return
	}
	defer f.Close()

	timestamp := time.Now().Format("2006-01-02 15:04:05")
	logEntry := fmt.Sprintf("\n### %s - %s\n%s\n", timestamp, role, content)
	f.WriteString(logEntry)
}

func LogToolCall(name string, args map[string]any, result string) {
	f, err := os.OpenFile(logFile, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		return
	}
	defer f.Close()

	timestamp := time.Now().Format("2006-01-02 15:04:05")
	logEntry := fmt.Sprintf("\n### %s - TOOL CALL: %s\n**Args:** %v\n**Result:**\n```text\n%s\n```\n", timestamp, name, args, result)
	f.WriteString(logEntry)
}
