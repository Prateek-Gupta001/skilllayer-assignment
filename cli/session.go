package main

import (
	"encoding/json"
	"os"

	"google.golang.org/genai"
)

const sessionFile = "chat_history.json"

func SaveHistory(history []*genai.Content) error {
	data, err := json.MarshalIndent(history, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(sessionFile, data, 0644)
}

func LoadHistory() ([]*genai.Content, error) {
	data, err := os.ReadFile(sessionFile)
	if err != nil {
		if os.IsNotExist(err) {
			return []*genai.Content{}, nil
		}
		return nil, err
	}
	var history []*genai.Content
	err = json.Unmarshal(data, &history)
	if err != nil {
		return []*genai.Content{}, nil
	}
	return history, nil
}
