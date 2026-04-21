//+------------------------------------------------------------------+
//|                                      MT5BridgeClient.mq5       |
//|  MetaTrader 5 Client Bridge for macOS Python API               |
//|                                                                  |
//|  This EA connects TO a Python server (instead of listening)   |
//|  Requires Python server to be running first                     |
//+------------------------------------------------------------------+
#property copyright "MT5 macOS Bridge"
#property version   "1.00"
#property strict

// Input parameters
input string ServerHost = "127.0.0.1";  // Python server IP
input int    ServerPort = 8222;         // Python server port
input int    ReconnectDelay = 5;        // Seconds between reconnect attempts

// Global variables
int          Socket = INVALID_HANDLE;    // INVALID_HANDLE = -1
string       ReceiveBuffer = "";
datetime     LastReconnectAttempt = 0;
int          TimerHandle = INVALID_HANDLE;  // Timer event handle

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   Print("============================================================");
   Print("MT5 Client Bridge initializing...");
   Print("Target server: ", ServerHost, ":", ServerPort);
   Print("EA Version: 1.00 (macOS Bridge)");
   Print("============================================================");

   // Reset connection state
   Socket = INVALID_HANDLE;
   ReceiveBuffer = "";
   LastReconnectAttempt = 0;

   // Attempt initial connection
   if(!ConnectToServer())
   {
      Print("[!] Initial connection failed, will retry in ", ReconnectDelay, " seconds");
      LastReconnectAttempt = TimeCurrent();
   }
   else
   {
      Print("[✓] Bridge EA initialized successfully");
   }

   // Start timer for more frequent checks (even without ticks)
   TimerHandle = EventSetTimer(1);  // 1 second timer
   if(TimerHandle == 0)
      Print("[!] Failed to set timer");
   else
      Print("[✓] Timer started (1 second interval)");

   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   Print("============================================================");
   Print("MT5 Client Bridge shutting down...");

   // Stop timer
   if(TimerHandle != INVALID_HANDLE)
   {
      EventKillTimer();
      TimerHandle = INVALID_HANDLE;
   }

   if(Socket != INVALID_HANDLE)
   {
      SocketClose(Socket);
      Socket = INVALID_HANDLE;
   }

   Print("[✓] Bridge EA stopped");
   Print("============================================================");
}

//+------------------------------------------------------------------+
//| Timer function                                                     |
//+------------------------------------------------------------------+
void OnTimer()
{
   // Same logic as OnTick - ensure connection is maintained
   OnTick();
}

//+------------------------------------------------------------------+
//| Expert tick function                                               |
//+------------------------------------------------------------------+
void OnTick()
{
   static int tickCount = 0;
   static datetime lastStatusPrint = 0;
   tickCount++;

   // Print status every 10 seconds when not connected
   if(Socket == INVALID_HANDLE && TimeCurrent() - lastStatusPrint >= 10)
   {
      Print("[STATUS] Not connected. Ticks: ", tickCount,
            " LastReconnect: ", TimeCurrent() - LastReconnectAttempt, "s ago");
      // Also show visual indicator on chart
      Comment("MT5 Bridge: DISCONNECTED\nCheck Experts tab for details\nRetrying every ", ReconnectDelay, " seconds");
      lastStatusPrint = TimeCurrent();
   }

   // Check connection
   if(Socket == INVALID_HANDLE)
   {
      // Try to reconnect periodically
      if(TimeCurrent() - LastReconnectAttempt >= ReconnectDelay)
      {
         Print("[RECONNECT] Attempting connection to ", ServerHost, ":", ServerPort, "...");
         if(ConnectToServer())
         {
            Print("[✓] Reconnected successfully!");
            Comment("MT5 Bridge: CONNECTED\nPython server: ", ServerHost, ":", ServerPort);
         }
         else
         {
            Print("[✗] Reconnect failed (error: ", GetLastError(), ")");
            Comment("MT5 Bridge: FAILED\nError: ", GetLastError(), "\nCheck server is running");
         }
         LastReconnectAttempt = TimeCurrent();
      }
      return;
   }

   // Update visual indicator
   Comment("MT5 Bridge: CONNECTED\nPython server: ", ServerHost, ":", ServerPort);

   // Process messages - SocketIsReadable will return 0 if no data
   // Only close connection on actual socket errors, not just no data
   ProcessClientMessages();
}

//+------------------------------------------------------------------+
//| Connect to Python server                                           |
//+------------------------------------------------------------------+
bool ConnectToServer()
{
   if(Socket != INVALID_HANDLE)
   {
      SocketClose(Socket);
      Socket = INVALID_HANDLE;
   }

   // Create socket with default flags
   Socket = SocketCreate();
   if(Socket == INVALID_HANDLE)
   {
      Print("Failed to create socket, error: ", GetLastError());
      return false;
   }

   Print("Connecting to ", ServerHost, ":", ServerPort, "...");

   // Connect to Python server with 5 second timeout
   if(!SocketConnect(Socket, ServerHost, ServerPort, 5000))
   {
      Print("Failed to connect to ", ServerHost, ":", ServerPort, ", error: ", GetLastError());
      Print("Make sure Python server is running!");
      SocketClose(Socket);
      Socket = INVALID_HANDLE;
      return false;
   }

   // Set timeouts (1 second for send/receive)
   SocketTimeouts(Socket, 1000, 1000);

   // Send initial PING to identify ourselves to the server
   string pingMsg = "PING\n";
   uchar pingData[];
   int pingLen = StringToCharArray(pingMsg, pingData, 0, WHOLE_ARRAY, CP_UTF8);
   if(pingLen > 0)
      SocketSend(Socket, pingData, pingLen - 1);

   Print("Connected to Python server!");
   return true;
}

//+------------------------------------------------------------------+
//| Process messages from Python                                       |
//+------------------------------------------------------------------+
void ProcessClientMessages()
{
   // Check how many bytes are available to read
   uint available = SocketIsReadable(Socket);

   if(available == 0)
      return;  // No data available

   // Read available data
   uchar buffer[];
   int bytesRead = SocketRead(Socket, buffer, available, 1000);

   if(bytesRead > 0)
   {
      // Convert bytes to string
      string data = CharArrayToString(buffer, 0, bytesRead, CP_UTF8);
      ReceiveBuffer += data;

      // Process complete messages
      ProcessCompleteMessages();
   }
   else if(bytesRead < 0)
   {
      // Error - close socket and trigger reconnect
      int err = GetLastError();
      Print("[!] Socket read error: ", err, " - closing connection");
      SocketClose(Socket);
      Socket = INVALID_HANDLE;
      Comment("MT5 Bridge: ERROR\nSocket error: ", err, "\nReconnecting...");
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
   if(Socket == INVALID_HANDLE)
      return;

   response += "\n";

   // Convert string to uchar array
   uchar data[];
   int len = StringToCharArray(response, data, 0, WHOLE_ARRAY, CP_UTF8);

   // Send data (excluding null terminator)
   if(len > 0)
      SocketSend(Socket, data, len - 1);
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
   else if(command == "SYMBOL_TOTAL" || command == "SYMBOLS_TOTAL")
      HandleSymbolTotal();
   else if(command == "SYMBOL_GET" || command == "SYMBOLS_GET")
      HandleSymbolGet(parts, count);
   else if(command == "SYMBOL_INFO")
      HandleSymbolInfo(parts, count);
   else if(command == "TICK" || command == "SYMBOL_TICK" || command == "SYMBOL_INFO_TICK")
      HandleTick(parts, count);
   else if(command == "SYMBOL_SELECT")
      HandleSymbolSelect(parts, count);
   else if(command == "ORDERS_TOTAL")
      HandleOrdersTotal();
   else if(command == "ORDERS_GET")
      HandleOrdersGet(parts, count);
   else if(command == "POSITIONS_TOTAL")
      HandlePositionsTotal();
   else if(command == "POSITIONS_GET")
      HandlePositionsGet(parts, count);
   else if(command == "ACCOUNT" || command == "ACCOUNT_INFO")
      HandleAccount();
   else if(command == "TERMINAL_INFO")
      HandleTerminalInfo();
   else if(command == "TRADE" || command == "ORDER_SEND" || command == "ORDER_CHECK")
      HandleTrade(parts, count);
   else if(command == "MARKET_BOOK_ADD")
      HandleMarketBookAdd(parts, count);
   else if(command == "MARKET_BOOK_GET")
      HandleMarketBookGet(parts, count);
   else if(command == "MARKET_BOOK_RELEASE")
      HandleMarketBookRelease(parts, count);
   else if(command == "SHUTDOWN")
      SendResponse("OK|result=disconnecting");
   else
      SendResponse("ERR|code=7|message=Unknown command: " + command);
}

void HandleInit(string &parts[], int count)
{
   // Check if this is from Python (has source=python param) or MT5 identification (bare INIT)
   string source = GetParam(parts, count, "source", "");

   if(source == "python")
   {
      // Python client calling initialize() - return success
      SendResponse("OK|success=true|path=" + TerminalInfoString(TERMINAL_PATH));
   }
   else
   {
      // Bare INIT - MT5 identification or compatibility
      SendResponse("OK|success=true|path=" + TerminalInfoString(TERMINAL_PATH));
   }
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

void HandleSymbolInfo(string &parts[], int count)
{
   string symbol = GetParam(parts, count, "symbol", "");

   if(StringLen(symbol) == 0)
   {
      SendResponse("ERR|code=2|message=Symbol required");
      return;
   }

   if(!SymbolSelect(symbol, true))
   {
      SendResponse("ERR|code=4|message=Symbol not found");
      return;
   }

   MqlTick tick;
   SymbolInfoTick(symbol, tick);

   SendResponse("OK|name=" + symbol +
                "|bid=" + DoubleToString(tick.bid, 5) +
                "|ask=" + DoubleToString(tick.ask, 5) +
                "|last=" + DoubleToString(tick.last, 5) +
                "|volume=" + IntegerToString((int)tick.volume) +
                "|digits=" + IntegerToString((int)SymbolInfoInteger(symbol, SYMBOL_DIGITS)) +
                "|spread=" + IntegerToString((int)SymbolInfoInteger(symbol, SYMBOL_SPREAD)) +
                "|point=" + DoubleToString(SymbolInfoDouble(symbol, SYMBOL_POINT), 10) +
                "|currency_base=" + SymbolInfoString(symbol, SYMBOL_CURRENCY_BASE) +
                "|currency_profit=" + SymbolInfoString(symbol, SYMBOL_CURRENCY_PROFIT) +
                "|description=" + SymbolInfoString(symbol, SYMBOL_DESCRIPTION));
}

void HandleSymbolSelect(string &parts[], int count)
{
   string symbol = GetParam(parts, count, "symbol", "");
   string enableStr = GetParam(parts, count, "enable", "true");

   if(StringLen(symbol) == 0)
   {
      SendResponse("ERR|code=2|message=Symbol required");
      return;
   }

   bool enable = (enableStr == "true" || enableStr == "1");
   bool result = SymbolSelect(symbol, enable);

   if(result)
      SendResponse("OK|result=true");
   else
      SendResponse("ERR|code=4|message=Failed to select symbol");
}

void HandleTerminalInfo()
{
   SendResponse("OK|connected=" + IntegerToString((int)TerminalInfoInteger(TERMINAL_CONNECTED)) +
                "|dlls_allowed=" + IntegerToString((int)TerminalInfoInteger(TERMINAL_DLLS_ALLOWED)) +
                "|trade_allowed=" + IntegerToString((int)TerminalInfoInteger(TERMINAL_TRADE_ALLOWED)) +
                "|path=" + TerminalInfoString(TERMINAL_PATH) +
                "|data_path=" + TerminalInfoString(TERMINAL_DATA_PATH) +
                "|common_data_path=" + TerminalInfoString(TERMINAL_COMMONDATA_PATH));
}

void HandleMarketBookAdd(string &parts[], int count)
{
   string symbol = GetParam(parts, count, "symbol", "");

   if(StringLen(symbol) == 0)
   {
      SendResponse("ERR|code=2|message=Symbol required");
      return;
   }

   if(MarketBookAdd(symbol))
      SendResponse("OK|result=true");
   else
      SendResponse("ERR|code=1|message=Failed to subscribe to market depth");
}

void HandleMarketBookGet(string &parts[], int count)
{
   string symbol = GetParam(parts, count, "symbol", "");

   if(StringLen(symbol) == 0)
   {
      SendResponse("ERR|code=2|message=Symbol required");
      return;
   }

   MqlBookInfo book[];
   int depth = MarketBookGet(symbol, book);

   if(depth == 0)
   {
      SendResponse("OK|data=[]");
      return;
   }

   string result = "OK|data=[";
   for(int i = 0; i < depth; i++)
   {
      if(i > 0) result += ",";
      result += "{\"type\":" + IntegerToString((int)book[i].type) +
                ",\"price\":" + DoubleToString(book[i].price, 5) +
                ",\"volume\":" + IntegerToString((int)book[i].volume) + "}";
   }
   result += "]";

   SendResponse(result);
}

void HandleMarketBookRelease(string &parts[], int count)
{
   string symbol = GetParam(parts, count, "symbol", "");

   if(StringLen(symbol) == 0)
   {
      SendResponse("ERR|code=2|message=Symbol required");
      return;
   }

   if(MarketBookRelease(symbol))
      SendResponse("OK|result=true");
   else
      SendResponse("ERR|code=1|message=Failed to unsubscribe from market depth");
}
