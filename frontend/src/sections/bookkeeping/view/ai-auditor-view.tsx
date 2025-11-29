'use client';

import { useState, useCallback, useRef, useEffect } from 'react';

import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import Stack from '@mui/material/Stack';
import InputBase from '@mui/material/InputBase';
import IconButton from '@mui/material/IconButton';
import Typography from '@mui/material/Typography';

import { DashboardContent } from 'src/layouts/dashboard';
import { useChatQuery } from 'src/actions/receipt';

import { Iconify } from 'src/components/iconify';
import { CustomBreadcrumbs } from 'src/components/custom-breadcrumbs';
import { LoadingScreen } from 'src/components/loading-screen';

import { paths } from 'src/routes/paths';
import { RouterLink } from 'src/routes/components';

import { fCurrency } from 'src/utils/format-number';

// ----------------------------------------------------------------------

type Message = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  receipts?: Array<{ id: string; receiptNumber: string; vendor: string; total: number }>;
  timestamp: Date;
};

export function AIAuditorView() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: 'Hello! I\'m your AI Auditor. I can help you analyze your receipts. Try asking me: "Show me all travel receipts above 100 EUR" or "How much did we spend on hardware last quarter?"',
      timestamp: new Date(),
    },
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { queryChat } = useChatQuery();

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = useCallback(async () => {
    if (!inputValue.trim() || isLoading) return;

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: inputValue,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    try {
      const response = await queryChat(inputValue);
      
      const assistantMessage: Message = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: response.answer,
        receipts: response.receipts,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      const errorMessage: Message = {
        id: `error-${Date.now()}`,
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  }, [inputValue, isLoading, queryChat]);

  const handleKeyPress = useCallback(
    (event: React.KeyboardEvent<HTMLInputElement>) => {
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        handleSendMessage();
      }
    },
    [handleSendMessage]
  );

  return (
    <DashboardContent>
      <CustomBreadcrumbs
        heading="AI Auditor"
        links={[
          { name: 'Dashboard', href: paths.dashboard.root },
          { name: 'AI Auditor' },
        ]}
        sx={{ mb: 3 }}
      />

      <Card
        sx={{
          height: 'calc(100vh - 200px)',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {/* Messages */}
        <Box
          sx={{
            flex: 1,
            overflowY: 'auto',
            p: 3,
            display: 'flex',
            flexDirection: 'column',
            gap: 2,
          }}
        >
          {messages.map((message) => (
            <Box
              key={message.id}
              sx={{
                display: 'flex',
                justifyContent: message.role === 'user' ? 'flex-end' : 'flex-start',
              }}
            >
              <Stack
                spacing={1}
                sx={{
                  maxWidth: '70%',
                  p: 2,
                  borderRadius: 2,
                  bgcolor: message.role === 'user' ? 'primary.main' : 'background.neutral',
                  color: message.role === 'user' ? 'primary.contrastText' : 'text.primary',
                }}
              >
                <Typography variant="body1">{message.content}</Typography>
                
                {message.receipts && message.receipts.length > 0 && (
                  <Stack spacing={1} sx={{ mt: 2 }}>
                    <Typography variant="caption" sx={{ fontWeight: 600 }}>
                      Related Receipts:
                    </Typography>
                    {message.receipts.map((receipt) => (
                      <Box
                        key={receipt.id}
                        component={RouterLink}
                        href={paths.dashboard.receipt.details(receipt.id)}
                        sx={{
                          p: 1.5,
                          borderRadius: 1,
                          bgcolor: message.role === 'user' ? 'rgba(255,255,255,0.1)' : 'background.paper',
                          textDecoration: 'none',
                          display: 'block',
                          '&:hover': {
                            bgcolor: message.role === 'user' ? 'rgba(255,255,255,0.2)' : 'action.hover',
                          },
                        }}
                      >
                        <Stack direction="row" justifyContent="space-between" alignItems="center">
                          <Stack>
                            <Typography variant="subtitle2" sx={{ color: 'inherit' }}>
                              {receipt.receiptNumber}
                            </Typography>
                            <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                              {receipt.vendor}
                            </Typography>
                          </Stack>
                          <Typography variant="subtitle2" sx={{ color: 'inherit' }}>
                            {fCurrency(receipt.total)}
                          </Typography>
                        </Stack>
                      </Box>
                    ))}
                  </Stack>
                )}

                <Typography variant="caption" sx={{ opacity: 0.7, fontSize: '0.7rem' }}>
                  {message.timestamp.toLocaleTimeString()}
                </Typography>
              </Stack>
            </Box>
          ))}

          {isLoading && (
            <Box sx={{ display: 'flex', justifyContent: 'flex-start' }}>
              <Stack
                spacing={1}
                sx={{
                  p: 2,
                  borderRadius: 2,
                  bgcolor: 'background.neutral',
                }}
              >
                <Typography variant="body2">Thinking...</Typography>
                <LoadingScreen />
              </Stack>
            </Box>
          )}

          <div ref={messagesEndRef} />
        </Box>

        {/* Input */}
        <Box
          sx={{
            p: 2,
            borderTop: (theme) => `1px solid ${theme.palette.divider}`,
          }}
        >
          <Stack direction="row" spacing={1} alignItems="center">
            <InputBase
              fullWidth
              placeholder="Ask me anything about your receipts..."
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              disabled={isLoading}
              sx={{
                p: 1.5,
                borderRadius: 1,
                bgcolor: 'background.neutral',
              }}
            />
            <IconButton
              color="primary"
              onClick={handleSendMessage}
              disabled={!inputValue.trim() || isLoading}
              sx={{ width: 48, height: 48 }}
            >
              <Iconify icon="solar:plain-bold" />
            </IconButton>
          </Stack>
        </Box>
      </Card>
    </DashboardContent>
  );
}

