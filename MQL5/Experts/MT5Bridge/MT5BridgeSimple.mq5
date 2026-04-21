//+------------------------------------------------------------------+
//|                                   MT5BridgeSimple.mq5            |
//|  Simplified MetaTrader 5 Socket Bridge - No external libs        |
//|                                                                  |
//|  This version uses MT5's built-in Socket* functions             |
//|  and simple string parsing instead of JSON library                |
//+------------------------------------------------------------------+
#property copyright "MT5 macOS Bridge"
#property version   "1.00"
#property strict

// Input parameters
input int    BridgePort = 8222;        // Bridge port number
input bool   AllowRemote = false;      // Allow remote connections

// Global variables
int          ServerSocket = INVALID_SOCKET;
int          ClientSocket = INVALID_SOCKET;
string       ReceiveBuffer = "";

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   Print("MT5 Simple Bridge initializing...");

   // Initialize socket library
   if(!SocketInitialize())
   {
      Print("Failed to initialize sockets");
      return(INIT_FAILED);
   }

   // Create server socket
   ServerSocket = SocketCreate();
   if(ServerSocket == INVALID_SOCKET)
   {
      Print("Failed to create socket: ", GetLastError());
      return(INIT_FAILED);
   }

   // Bind to address
   string bindAddr = AllowRemote ? "0.0.0.0" : "127.0.0.1";
   if(!SocketBind(ServerSocket, bindAddr, BridgePort))
   {
      Print("Failed to bind to port ", BridgePort, ": ", GetLastError());
      SocketClose(ServerSocket);
      return(INIT_FAILED);
   }

   // Start listening
   if(!SocketListen(ServerSocket, 1))
   {
      Print("Failed to listen: ", GetLastError());
      SocketClose(ServerSocket);
      return(INIT_FAILED);
   }

   // Set non-blocking mode
   SocketIsBlocking(ServerSocket, false);

   Print("MT5 Simple Bridge listening on ", bindAddr, ":", BridgePort);
   Print("Add this EA to any chart to enable Python API access");

   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   Print("MT5 Simple Bridge shutting down...");

   if(ClientSocket != INVALID_SOCKET)
   {
      SocketClose(ClientSocket);
      ClientSocket = INVALID_SOCKET;
   }

   if(ServerSocket != INVALID_SOCKET)
   {
      SocketClose(ServerSocket);
      ServerSocket = INVALID_SOCKET;
   }

   SocketUninitialize();
   Print("MT5 Simple Bridge stopped");
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
   // Accept new connections
   if(ClientSocket == INVALID_SOCKET)
   {
      ClientSocket = SocketAccept(ServerSocket, 0);
      if(ClientSocket != INVALID_SOCKET)
      {
         Print("Python client connected");
         SocketIsBlocking(ClientSocket, false);
         ReceiveBuffer = "";
      }
   }

   // Process client messages
   if(ClientSocket != INVALID_SOCKET)
   {
      ProcessClientMessages();
   }
}

//+------------------------------------------------------------------+
//| Process messages from client                                     |
//+------------------------------------------------------------------+
void ProcessClientMessages()
{
   uchar buffer[4096];
   uint received = SocketRead(ClientSocket, buffer, 4096, 0);

   if(received > 0)
   {
      // Convert bytes to string
      string data = "";
      for(uint i = 0; i < received; i++)
         data += CharToString((char)buffer[i]);

      ReceiveBuffer += data;

      // Process complete messages (format: LEN:json\n)
      ProcessCompleteMessages();
   }
   else if(received == 0 && SocketIsConnected(ClientSocket) == false)
   {
      // Connection closed
      Print("Python client disconnected");
      SocketClose(ClientSocket);
      ClientSocket = INVALID_SOCKET;
      ReceiveBuffer = "";
   }
}

//+------------------------------------------------------------------+
//| Process complete messages from buffer                            |
//+------------------------------------------------------------------+
void ProcessCompleteMessages()
{
   int pos = StringFind(ReceiveBuffer, "\n");

   while(pos >= 0)
   {
      string msg = StringSubstr(ReceiveBuffer, 0, pos);
      ReceiveBuffer = StringSubstr(ReceiveBuffer, pos + 1);

      // Handle the command
      HandleCommand(msg);

      pos = StringFind(ReceiveBuffer, "\n");
   }
}

//+------------------------------------------------------------------+
//| Simple JSON-like parser and command handler                      |
//+------------------------------------------------------------------+
void HandleCommand(string cmd)
{
   // Expected format: CMD|PARAM1=VAL1|PARAM2=VAL2|...
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

//+------------------------------------------------------------------+
//| Send response to client                                          |
//+------------------------------------------------------------------+
void SendResponse(string response)
{
   if(ClientSocket == INVALID_SOCKET)
      return;

   response += "\n";
   uchar data[];
   StringToCharArray(response, data, 0, StringLen(response), CP_UTF8);
   SocketWrite(ClientSocket, data, StringLen(response));
}

//+------------------------------------------------------------------+
//| Parse parameter value                                            |
//+------------------------------------------------------------------+
string GetParam(string parts[], int count, string key, string defaultVal = "")
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
//| Command Handlers                                                  |
//+------------------------------------------------------------------+

void HandleInit(string parts[], int count)
{
   string login = GetParam(parts, count, "login", "0");
   string server = GetParam(parts, count, "server", "");

   // Check terminal status
   if(!TerminalInfoInteger(TERMINAL_CONNECTED))
   {
      SendResponse("ERR|code=31|message=Not connected to broker");
      return;
   }

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

void HandleSymbolGet(string parts[], int count)
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

void HandleTick(string parts[], int count)
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

void HandleOrdersGet(string parts[], int count)
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

void HandlePositionsGet(string parts[], int count)
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
   if(!AccountInfoInteger(ACCOUNT_LOGIN))
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

void HandleTrade(string parts[], int count)
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

   // Check trade allowed
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

   // Get price if not specified
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
