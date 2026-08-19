package main

import (
	"bufio"
	"context"
	"fmt"
	"log"
	"os"
	"strings"

	"google.golang.org/genai"
)

func main() {
	ctx := context.Background()
	apiKey := os.Getenv("GEMINI_API_KEY")
	if apiKey == "" {
		log.Fatal("Please set the GEMINI_API_KEY environment variable.")
	}

	client, err := genai.NewClient(ctx, &genai.ClientConfig{
		APIKey:  apiKey,
		Backend: genai.BackendGeminiAPI,
	})
	if err != nil {
		log.Fatalf("Failed to create client: %v", err)
	}

	history, err := LoadHistory()
	if err != nil {
		log.Printf("Warning: Could not load history: %v", err)
		history = []*genai.Content{}
	}

	fmt.Println("Welcome to SkillLayer Brain CLI!")
	if len(history) > 0 {
		fmt.Println("1. Start a new chat")
		fmt.Println("2. Resume last chat")
		fmt.Print("> ")
		var choice string
		fmt.Scanln(&choice)
		if choice == "1" {
			history = []*genai.Content{}
			fmt.Println("Starting a new chat session.")
		} else {
			fmt.Println("Resuming last chat session.")
		}
	} else {
		fmt.Println("Starting a new chat session.")
	}

	config := &genai.GenerateContentConfig{
		Tools:             GetTools(),
		SystemInstruction: &genai.Content{Parts: []*genai.Part{{Text: SystemPrompt}}},
		Temperature:       genai.Ptr(float32(0.7)),
	}

	chat, err := client.Chats.Create(ctx, "gemini-2.5-flash", config, history)
	if err != nil {
		log.Fatalf("Failed to create chat: %v", err)
	}

	fmt.Println("\nType your query (or type 'exit' to quit):")
	reader := bufio.NewReader(os.Stdin)

	for {
		fmt.Print("\nYou: ")
		userInput, err := reader.ReadString('\n')
		if err != nil {
			log.Fatal(err)
		}
		userInput = strings.TrimSpace(userInput)

		if strings.ToLower(userInput) == "exit" || strings.ToLower(userInput) == "quit" {
			fmt.Println("Goodbye!")
			break
		}
		if userInput == "" {
			continue
		}

		LogInteraction("User", userInput)

		// The new SDK's SendMessage expects value types, not pointers
		partsToSend := []genai.Part{{Text: userInput}}

		for {
			result, err := chat.SendMessage(ctx, partsToSend...)
			if err != nil {
				fmt.Printf("Error sending message: %v\n", err)
				break
			}

			if len(result.Candidates) == 0 || result.Candidates[0].Content == nil {
				fmt.Println("No response from model.")
				break
			}

			respParts := result.Candidates[0].Content.Parts
			var functionCalls []*genai.FunctionCall
			var textResponse string

			for _, part := range respParts {
				if part.FunctionCall != nil {
					functionCalls = append(functionCalls, part.FunctionCall)
				}
				if part.Text != "" {
					textResponse += part.Text
				}
			}

			if len(functionCalls) > 0 {
				var responseParts []genai.Part

				for _, fc := range functionCalls {
					fmt.Printf("[Tool Call: %s] %v\n", fc.Name, fc.Args)
					resultStr := ExecuteTool(ctx, fc.Name, fc.Args)
					LogToolCall(fc.Name, fc.Args, resultStr)

					responseParts = append(responseParts, genai.Part{
						FunctionResponse: &genai.FunctionResponse{
							Name:     fc.Name,
							Response: map[string]any{"result": resultStr},
						},
					})
				}
				partsToSend = responseParts // Send tool results back to LLM
				continue
			} else {
				if textResponse != "" {
					fmt.Printf("\nAssistant: %s\n", textResponse)
					LogInteraction("Assistant", textResponse)

					// Save chat history to disk
					currentHistory := chat.History(false)
					SaveHistory(currentHistory)
				}
				break // Wait for next user input
			}
		}
	}
}
