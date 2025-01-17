import React, { useState, useEffect, useRef } from 'react';
import { Input } from './ui/input';
import { Send } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { CopyButton } from './ui/copy-button';
import { TypingIndicator } from './ui/typing-indicator';

const IconWrapper = ({ icon: Icon }: { icon: LucideIcon }) => {
  return <Icon className="w-5 h-5" />;
};

interface Message {
  type: 'ai' | 'user';
  content: string;
  visualizations?: Array<{
    type: string;
    path: string;
    description: string;
  }>;
  isInitial?: boolean;
}

export function ContentGeneratorApp() {
  const [isGenerating, setIsGenerating] = useState(false);
  const [prompt, setPrompt] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    // Add initial greeting message
    setMessages([{
      type: 'ai',
      content: "Hi! I'm an AI agent specialized in content writing. I can help you create various types of content, from concise tweets to detailed academic papers and data analysis. What topic would you like me to write about?",
      isInitial: true
    }]);
  }, []);

  useEffect(() => {
    // Scroll to bottom whenever messages change
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const generateContent = async () => {
    if (!prompt.trim()) {
      setError('Please enter a prompt');
      return;
    }

    setIsGenerating(true);
    setError(null);
    // Clear input immediately
    const currentPrompt = prompt;
    setPrompt('');

    // Add user message
    setMessages(prev => [...prev, { type: 'user', content: currentPrompt }]);

    // Add temporary AI message with typing indicator
    setMessages(prev => [...prev, { type: 'ai', content: '' }]);

    try {
      const response = await fetch('http://localhost:8000/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: currentPrompt })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      let accumulatedContent = '';
      let currentVisualizations: any[] = [];

      if (reader) {
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const messages = buffer.split('\n\n');
          buffer = messages.pop() || '';

          for (const message of messages) {
            const trimmedMessage = message.trim();
            if (!trimmedMessage) continue;

            if (trimmedMessage.startsWith('data: ')) {
              const jsonStr = trimmedMessage.slice(5).trim();

              if (jsonStr === '[DONE]') {
                continue;
              }

              try {
                const parsedData = JSON.parse(jsonStr);
                if (parsedData.content) {
                  accumulatedContent += parsedData.content;
                  if (parsedData.visualizations) {
                    currentVisualizations = parsedData.visualizations;
                  }
                  // Update the last AI message
                  setMessages(prev => {
                    const newMessages = [...prev];
                    newMessages[newMessages.length - 1] = {
                      type: 'ai',
                      content: accumulatedContent,
                      visualizations: currentVisualizations
                    };
                    return newMessages;
                  });
                } else if (parsedData.error) {
                  setError(parsedData.error);
                }
              } catch (e) {
                console.debug('Skipping unparseable message:', trimmedMessage);
                continue;
              }
            }
          }
        }

        decoder.decode(undefined);
      }
    } catch (error) {
      console.error('API error:', error);
      setError(error instanceof Error ? error.message : 'Failed to generate content');
      // Remove the temporary AI message if there was an error
      setMessages(prev => prev.slice(0, -1));
    } finally {
      setIsGenerating(false);
      inputRef.current?.focus(); // Focus input after sending
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      generateContent();
    }
  };

  return (
    <div className="min-h-screen bg-gray-900 flex flex-col">
      {/* Header */}
      <div className="bg-gray-800 border-b border-gray-700 px-4 py-3 shadow-lg">
        <div className="max-w-3xl mx-auto">
          <h1 className="text-xl font-semibold text-white">Agent Orch 1.0</h1>
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-hidden flex flex-col">
        <div className="flex-1 overflow-y-auto px-4 py-6">
          <div className="max-w-3xl mx-auto space-y-4">
            {messages.map((message, index) => (
              <div
                key={index}
                className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div className="flex flex-col max-w-[80%] group">
                  <div
                    className={`
                      rounded-2xl px-4 py-2 shadow-sm
                      ${message.type === 'user'
                        ? 'bg-blue-500 text-white rounded-br-none'
                        : 'bg-gray-800 text-gray-100 rounded-bl-none'
                      }
                    `}
                  >
                    {message.content ? (
                      <pre className="whitespace-pre-wrap font-sans text-sm">
                        {message.content}
                      </pre>
                    ) : (
                      <TypingIndicator />
                    )}
                  </div>
                  {message.type === 'ai' && !message.isInitial && message.content && (
                    <div className="mt-1 ml-2">
                      <CopyButton text={message.content} />
                    </div>
                  )}
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Fixed Input Area */}
        <div className="bg-gray-800 border-t border-gray-700 px-4 py-3">
          <div className="max-w-3xl mx-auto">
            {error && (
              <div className="mb-3 px-3 py-2 bg-red-900/50 border border-red-700 rounded-lg text-red-200 text-sm">
                {error}
              </div>
            )}
            <div className="flex items-center gap-2">
              <Input
                ref={inputRef}
                placeholder="What would you like me to write about?"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                onKeyPress={handleKeyPress}
                className="flex-1 bg-gray-700/50 border-gray-600 focus:ring-blue-500 focus:border-blue-500 rounded-full py-2 px-4"
                disabled={isGenerating}
              />
              <button
                onClick={generateContent}
                disabled={isGenerating}
                className="w-10 h-10 flex items-center justify-center bg-blue-500 hover:bg-blue-600 disabled:bg-blue-400 text-white rounded-full shadow-sm transition-colors"
              >
                <IconWrapper icon={Send} />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}