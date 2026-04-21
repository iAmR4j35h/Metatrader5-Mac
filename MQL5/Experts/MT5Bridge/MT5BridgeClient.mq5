//+------------------------------------------------------------------+
//|                                      MT5BridgeClient.mq5       |
//|  MetaTrader 5 Client Bridge for macOS Python API               |
//|                                                                  |
//|  This EA connects TO a Python server (instead of listening)     |
//|  Requires Python server to be running first                       |
//+------------------------------------------------------------------+
#property copyright "MT5 macOS Bridge"
#property version   "1.00"
#property strict

// Input parameters
input string ServerHost = "127.0.0.1";  // Python server IP
input int    ServerPort = 8222;         // Python server port
input int    ReconnectDelay = 5;        // Seconds between reconnect attempts

// Global variables
int          Socket = INVALID_SOCKET;
string       ReceiveBuffer = "";
datetime     LastReconnectAttempt = 0;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   Print("MT5 Client Bridge initializing...");
   Print("Will connect to Python server at ", ServerHost, ":", ServerPort);

   // Attempt initial connection
   if(!ConnectToServer())
   {
      Print("Will retry connection in ", ReconnectDelay, " seconds");
   }

   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                   |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   Print("MT5 Client Bridge shutting down...");

   if(Socket != INVALID_SOCKET)
   {
      SocketClose(Socket);
      Socket = INVALID_SOCKET;
   }

   Print("MT5 Client Bridge stopped");
}

//+------------------------------------------------------------------+
//| Expert tick function                                               |
//+------------------------------------------------------------------+
void OnTick()
{
   // Check connection
   if(Socket == INVALID_SOCKET)
   {
      // Try to reconnect periodically
      if(TimeCurrent() - LastReconnectAttempt >= ReconnectDelay)
      {
         ConnectToServer();
         LastReconnectAttempt = TimeCurrent();
      }
      return;
   }

   // Check if still connected
   if(!SocketIsConnected(Socket))
   {
      Print("Connection lost, will reconnect...");
      SocketClose(Socket);
      Socket = INVALID_SOCKET;
      return;
   }

   // Process messages
   ProcessClientMessages();
}

//+------------------------------------------------------------------+
//| Connect to Python server                                           |
//+------------------------------------------------------------------+
bool ConnectToServer()
{
   if(Socket != INVALID_SOCKET)
   {
      SocketClose(Socket);
      Socket = INVALID_SOCKET;
   }

   // Create socket
   Socket = SocketCreate();
   if(Socket == INVALID_SOCKET)
   {
      Print("Failed to create socket");
      return false;
   }

   // Connect to Python server
   if(!SocketConnect(Socket, ServerHost, ServerPort, 5000))
   {
      Print("Failed to connect to ", ServerHost, ":", ServerPort);
      Print("Make sure Python server is running: python -m MetaTrader5.server");
      SocketClose(Socket);
      Socket = INVALID_SOCKET;
      return false;
   }

   // Set non-blocking mode
   SocketIsBlocking(Socket, false);

   Print("✓ Connected to Python server at ", ServerHost, ":", ServerPort);
   return true;
}

//+------------------------------------------------------------------+
//| Process messages from Python                                       |
//+------------------------------------------------------------------+
void ProcessClientMessages()
{
   uchar buffer[4096];
   int received = SocketReceive(Socket, buffer, 4096, 10);

   if(received > 0)
   {
      // Convert bytes to string
      string data = CharArrayToString(buffer, 0, received, CP_UTF8);
      ReceiveBuffer += data;

      // Process complete messages
      ProcessCompleteMessages();
   }
   else if(received < 0)
   {
      // Connection error
      Print("Receive error, disconnecting");
      SocketClose(Socket);
      Socket = INVALID_SOCKET;
   }
}

//+------------------------------------------------------------------+
//| Process complete messages from buffer                              |
//+------------------------------------------------------------------+
void ProcessCompleteMessages()
{
   int newlinePos = StringFind(ReceiveBuffer, "\n");

   while(newlinePos != -1)
   {
      string message = StringSubstr(ReceiveBuffer, 0, newlinePos);
      ReceiveBuffer = StringSubstr(ReceiveBuffer, newlinePos + 1);

      // Handle the command
      HandleCommand(message);

      newlinePos = StringFind(ReceiveBuffer, "\n");
   }
}

//+------------------------------------------------------------------+
//| Send response to Python                                            |
//+------------------------------------------------------------------+
void SendResponse(string response)
{
   if(Socket == INVALID_SOCKET)
      return;

   response += "\n";
   uchar data[];
   StringToCharArray(response, data, 0, WHOLE_ARRAY, CP_UTF8);
   SocketSend(Socket, data, ArraySize(data));
}

//+------------------------------------------------------------------+
//| Parse parameter value                                              |
//+------------------------------------------------------------------+
string GetParam(string &parts[], int count, string key, string defaultVal = "")
{
   string prefix = key + "=";
   for(int i = 1; i < count; i++)
   {
      if(StringFind(parts[i], prefix) == 0)
         return StringSubstr(parts[i], StringLen(prefix));
   }
   return defaultVal;
}

//+------------------------------------------------------------------+
//| Command Handlers                                                   |
//+------------------------------------------------------------------+

void HandleCommand(string cmd)
{
   // Format: CMD|PARAM1=VAL1|PARAM2=VAL2
   string parts[];
   int count = StringSplit(cmd, '|', parts);

   if(count < 1)
   {
      SendResponse("ERR|code=2|message=Invalid format");
      return;
   }

   string command = parts[0];

   if(command == "PING")
      SendResponse("OK|result=pong");
   else if(command == "INIT")
      HandleInit(parts, count);
   else if(command == "VERSION")
      HandleVersion();
   else if(command == "SYMBOL_TOTAL")
      HandleSymbolTotal();
   else if(command == "SYMBOL_GET")
      HandleSymbolGet(parts, count);
   else if(command == "TICK")
      HandleTick(parts, count);
   else if(command == "ORDERS_TOTAL")
      HandleOrdersTotal();
   else if(command == "ORDERS_GET")
      HandleOrdersGet(parts, count);
   else if(command == "POSITIONS_TOTAL")
      HandlePositionsTotal();
   else if(command == "POSITIONS_GET")
      HandlePositionsGet(parts, count);
   else if(command == "ACCOUNT")
      HandleAccount();
   else if(command == "TRADE")
      HandleTrade(parts, count);
   else
      SendResponse("ERR|code=7|message=Unknown command: " + command);
}

void HandleInit(string &parts[], int count)
{
   SendResponse("OK|success=true|path=" + TerminalInfoString(TERMINAL_PATH));
}

void HandleVersion()
{
   long build = TerminalInfoInteger(TERMINAL_BUILD);
   SendResponse("OK|version=5.0|build=" + IntegerToString(build));
}

void HandleSymbolTotal()
{
   int total = SymbolsTotal(false);
   SendResponse("OK|total=" + IntegerToString(total));
}

void HandleSymbolGet(string &parts[], int count)
{
   string group = GetParam(parts, count, "group", "");
   string result = "OK|symbols=";

   int total = SymbolsTotal(false);
   bool first = true;

   for(int i = 0; i < total; i++)
   {
      string name = SymbolName(i, false);
      if(StringLen(group) == 0 || StringFind(name, group) >= 0)
      {
         if(!first)
            result += ",";
         result += name;
         first = false;
      }
   }

   SendResponse(result);
}

void HandleTick(string &parts[], int count)
{
   string symbol = GetParam(parts, count, "symbol", "");

   if(StringLen(symbol) == 0)
   {
      SendResponse("ERR|code=2|message=Symbol required");
      return;
   }

   MqlTick tick;
   if(!SymbolInfoTick(symbol, tick))
   {
      SendResponse("ERR|code=4|message=Symbol not found");
      return;
   }

   SendResponse("OK|time=" + IntegerToString((int)tick.time) +
                "|bid=" + DoubleToString(tick.bid, 5) +
                "|ask=" + DoubleToString(tick.ask, 5) +
                "|last=" + DoubleToString(tick.last, 5) +
                "|volume=" + IntegerToString((int)tick.volume));
}

void HandleOrdersTotal()
{
   int total = OrdersTotal();
   SendResponse("OK|total=" + IntegerToString(total));
}

void HandleOrdersGet(string &parts[], int count)
{
   string symbol = GetParam(parts, count, "symbol", "");
   string result = "OK|orders=";

   int total = OrdersTotal();
   bool first = true;

   for(int i = 0; i < total; i++)
   {
      ulong ticket = OrderGetTicket(i);
      if(ticket == 0)
         continue;

      string sym = OrderGetString(ORDER_SYMBOL);
      if(StringLen(symbol) > 0 && sym != symbol)
         continue;

      if(!first)
         result += ";";

      result += IntegerToString((int)ticket) + "," + sym +
                "," + IntegerToString((int)OrderGetInteger(ORDER_TYPE)) +
                "," + DoubleToString(OrderGetDouble(ORDER_VOLUME_CURRENT), 2);
      first = false;
   }

   SendResponse(result);
}

void HandlePositionsTotal()
{
   int total = PositionsTotal();
   SendResponse("OK|total=" + IntegerToString(total));
}

void HandlePositionsGet(string &parts[], int count)
{
   string symbol = GetParam(parts, count, "symbol", "");
   string result = "OK|positions=";

   int total = PositionsTotal();
   bool first = true;

   for(int i = 0; i < total; i++)
   {
      string sym = PositionGetSymbol(i);
      if(StringLen(sym) == 0)
         continue;
      if(StringLen(symbol) > 0 && sym != symbol)
         continue;

      if(!first)
         result += ";";

      result += IntegerToString((int)PositionGetInteger(POSITION_TICKET)) +
                "," + sym +
                "," + IntegerToString((int)PositionGetInteger(POSITION_TYPE)) +
                "," + DoubleToString(PositionGetDouble(POSITION_VOLUME), 2) +
                "," + DoubleToString(PositionGetDouble(POSITION_PROFIT), 2);
      first = false;
   }

   SendResponse(result);
}

void HandleAccount()
{
   if(AccountInfoInteger(ACCOUNT_LOGIN) == 0)
   {
      SendResponse("ERR|code=6|message=Not logged in");
      return;
   }

   SendResponse("OK|login=" + IntegerToString((int)AccountInfoInteger(ACCOUNT_LOGIN)) +
                "|server=" + AccountInfoString(ACCOUNT_SERVER) +
                "|currency=" + AccountInfoString(ACCOUNT_CURRENCY) +
                "|balance=" + DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE), 2) +
                "|equity=" + DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY), 2) +
                "|margin=" + DoubleToString(AccountInfoDouble(ACCOUNT_MARGIN), 2) +
                "|margin_free=" + DoubleToString(AccountInfoDouble(ACCOUNT_MARGIN_FREE), 2));
}

void HandleTrade(string &parts[], int count)
{
   string action = GetParam(parts, count, "action", "1");
   string symbol = GetParam(parts, count, "symbol", "");
   string volume = GetParam(parts, count, "volume", "0.01");
   string type = GetParam(parts, count, "type", "0");
   string price = GetParam(parts, count, "price", "0");
   string sl = GetParam(parts, count, "sl", "0");
   string tp = GetParam(parts, count, "tp", "0");
   string comment = GetParam(parts, count, "comment", "");

   if(StringLen(symbol) == 0)
   {
      SendResponse("ERR|code=2|message=Symbol required");
      return;
   }

   if(!TerminalInfoInteger(TERMINAL_TRADE_ALLOWED))
   {
      SendResponse("ERR|code=8|message=Trading not allowed");
      return;
   }

   if(!MQLInfoInteger(MQL_TRADE_ALLOWED))
   {
      SendResponse("ERR|code=8|message=EA trading not allowed");
      return;
   }

   MqlTradeRequest request = {};
   MqlTradeResult tradeResult = {};

   request.action = (ENUM_TRADE_REQUEST_ACTIONS)StringToInteger(action);
   request.symbol = symbol;
   request.volume = StringToDouble(volume);
   request.type = (ENUM_ORDER_TYPE)StringToInteger(type);

   if(StringToDouble(price) == 0)
   {
      MqlTick tick;
      SymbolInfoTick(symbol, tick);
      if(request.type == ORDER_TYPE_BUY)
         request.price = tick.ask;
      else
         request.price = tick.bid;
   }
   else
   {
      request.price = StringToDouble(price);
   }

   request.deviation = 10;

   if(StringToDouble(sl) > 0)
      request.sl = StringToDouble(sl);
   if(StringToDouble(tp) > 0)
      request.tp = StringToDouble(tp);
   if(StringLen(comment) > 0)
      request.comment = comment;

   if(!OrderSend(request, tradeResult))
   {
      SendResponse("ERR|code=1|message=OrderSend failed");
      return;
   }

   SendResponse("OK|retcode=" + IntegerToString((int)tradeResult.retcode) +
                "|order=" + IntegerToString((int)tradeResult.order) +
                "|deal=" + IntegerToString((int)tradeResult.deal) +
                "|volume=" + DoubleToString(tradeResult.volume, 2) +
                "|price=" + DoubleToString(tradeResult.price, 5));
}
