//+------------------------------------------------------------------+
//|                                              MT5Bridge.mq5       |
//|  MetaTrader 5 Socket Bridge for macOS Python API               |
//|                                                                  |
//|  This EA runs in MT5 and accepts TCP socket connections from     |
//|  the Python API on macOS, translating JSON commands to MQL5     |
//|  function calls.                                                |
//+------------------------------------------------------------------+
#property copyright "MT5 macOS Bridge"
#property link      ""
#property version   "1.00"
#property strict

#include <JAson.mqh>  // JSON library (need to download)
#include <Sockets.mqh> // Socket library (need to download)

// Input parameters
input int    BridgePort = 8222;        // Bridge port number
input string BridgeBindAddress = "0.0.0.0"; // Bind address (0.0.0.0 for all)
input int    MaxConnections = 5;       // Maximum concurrent connections
input bool   AllowRemote = false;      // Allow remote connections (security risk)

// Global variables
CSocket*     ServerSocket = NULL;
CSocket*     ClientSockets[];
string       Buffer[];                   // Receive buffer per connection
bool         IsAuthenticated[];

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   Print("MT5 Bridge initializing...");

   // Create server socket
   ServerSocket = new CSocket();
   if(!ServerSocket.Create(AF_INET, SOCK_STREAM, IPPROTO_TCP))
   {
      Print("Failed to create socket: ", GetLastError());
      return(INIT_FAILED);
   }

   // Allow address reuse
   ServerSocket.SetSockOpt(SO_REUSEADDR, 1);

   // Bind to address
   string bindAddr = AllowRemote ? BridgeBindAddress : "127.0.0.1";
   if(!ServerSocket.Bind(bindAddr, BridgePort))
   {
      Print("Failed to bind to port ", BridgePort, ": ", GetLastError());
      ServerSocket.Close();
      delete ServerSocket;
      return(INIT_FAILED);
   }

   // Start listening
   if(!ServerSocket.Listen(MaxConnections))
   {
      Print("Failed to listen: ", GetLastError());
      ServerSocket.Close();
      delete ServerSocket;
      return(INIT_FAILED);
   }

   // Set non-blocking mode
   ServerSocket.BlockingMode(false);

   // Initialize arrays
   ArrayResize(ClientSockets, 0);
   ArrayResize(Buffer, 0);
   ArrayResize(IsAuthenticated, 0);

   Print("MT5 Bridge listening on ", bindAddr, ":", BridgePort);
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   Print("MT5 Bridge shutting down...");

   // Close all client connections
   for(int i = 0; i < ArraySize(ClientSockets); i++)
   {
      if(ClientSockets[i] != NULL)
      {
         ClientSockets[i].Close();
         delete ClientSockets[i];
      }
   }
   ArrayResize(ClientSockets, 0);
   ArrayResize(Buffer, 0);
   ArrayResize(IsAuthenticated, 0);

   // Close server socket
   if(ServerSocket != NULL)
   {
      ServerSocket.Close();
      delete ServerSocket;
      ServerSocket = NULL;
   }

   Print("MT5 Bridge stopped");
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
   AcceptNewConnections();
   ProcessClientMessages();
}

//+------------------------------------------------------------------+
//| Accept new incoming connections                                  |
//+------------------------------------------------------------------+
void AcceptNewConnections()
{
   if(ServerSocket == NULL) return;

   CSocket* client = ServerSocket.Accept();
   if(client != NULL)
   {
      int idx = ArraySize(ClientSockets);
      ArrayResize(ClientSockets, idx + 1);
      ArrayResize(Buffer, idx + 1);
      ArrayResize(IsAuthenticated, idx + 1);

      ClientSockets[idx] = client;
      Buffer[idx] = "";
      IsAuthenticated[idx] = false;

      // Set non-blocking mode
      client.BlockingMode(false);

      Print("New client connection #", idx);
   }
}

//+------------------------------------------------------------------+
//| Process messages from all connected clients                        |
//+------------------------------------------------------------------+
void ProcessClientMessages()
{
   for(int i = ArraySize(ClientSockets) - 1; i >= 0; i--)
   {
      if(ClientSockets[i] == NULL) continue;

      char recvBuf[4096];
      int received = ClientSockets[i].Receive(recvBuf, 4096, 0);

      if(received > 0)
      {
         // Convert received bytes to string
         string data = CharArrayToString(recvBuf, 0, received, CP_UTF8);
         Buffer[i] += data;

         // Process complete messages (format: [4-byte length][JSON])
         ProcessCompleteMessages(i);
      }
      else if(received == 0)
      {
         // Connection closed
         Print("Client ", i, " disconnected");
         ClientSockets[i].Close();
         delete ClientSockets[i];
         ClientSockets[i] = NULL;
         RemoveClient(i);
      }
      else if(received < 0)
      {
         int err = GetLastError();
         if(err != WSAEWOULDBLOCK && err != WSAEINPROGRESS)
         {
            // Real error
            Print("Client ", i, " error: ", err);
            ClientSockets[i].Close();
            delete ClientSockets[i];
            ClientSockets[i] = NULL;
            RemoveClient(i);
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Remove client from arrays                                        |
//+------------------------------------------------------------------+
void RemoveClient(int idx)
{
   int size = ArraySize(ClientSockets);
   for(int i = idx; i < size - 1; i++)
   {
      ClientSockets[i] = ClientSockets[i + 1];
      Buffer[i] = Buffer[i + 1];
      IsAuthenticated[i] = IsAuthenticated[i + 1];
   }
   ArrayResize(ClientSockets, size - 1);
   ArrayResize(Buffer, size - 1);
   ArrayResize(IsAuthenticated, size - 1);
}

//+------------------------------------------------------------------+
//| Process complete messages from buffer                            |
//+------------------------------------------------------------------+
void ProcessCompleteMessages(int clientIdx)
{
   while(StringLen(Buffer[clientIdx]) >= 4)
   {
      // Get message length (4 bytes, little-endian)
      string lenStr = StringSubstr(Buffer[clientIdx], 0, 4);
      int msgLen = StringToInteger(lenStr, 16); // Simplified - need proper byte conversion

      if(StringLen(Buffer[clientIdx]) < 4 + msgLen)
         break; // Wait for more data

      // Extract JSON message
      string jsonMsg = StringSubstr(Buffer[clientIdx], 4, msgLen);
      Buffer[clientIdx] = StringSubstr(Buffer[clientIdx], 4 + msgLen);

      // Handle the command
      HandleCommand(clientIdx, jsonMsg);
   }
}

//+------------------------------------------------------------------+
//| Handle a single command                                          |
//+------------------------------------------------------------------+
void HandleCommand(int clientIdx, string jsonCmd)
{
   CJAVal json;
   if(!json.Deserialize(jsonCmd))
   {
      SendResponse(clientIdx, "{\"error\":\"Invalid JSON\",\"error_code\":-2}");
      return;
   }

   string cmd = json["cmd"].ToStr();
   CJAVal params = json["params"];
   CJAVal result;

   Print("Received command: ", cmd);

   // Route command to appropriate handler
   if(cmd == "ping")
      result["result"] = "pong";
   else if(cmd == "initialize")
      HandleInitialize(params, result);
   else if(cmd == "shutdown")
      HandleShutdown(params, result);
   else if(cmd == "version")
      HandleVersion(params, result);
   else if(cmd == "terminal_info")
      HandleTerminalInfo(params, result);
   else if(cmd == "symbols_total")
      HandleSymbolsTotal(params, result);
   else if(cmd == "symbols_get")
      HandleSymbolsGet(params, result);
   else if(cmd == "symbol_info")
      HandleSymbolInfo(params, result);
   else if(cmd == "symbol_info_tick")
      HandleSymbolInfoTick(params, result);
   else if(cmd == "symbol_select")
      HandleSymbolSelect(params, result);
   else if(cmd == "market_book_add")
      HandleMarketBookAdd(params, result);
   else if(cmd == "market_book_get")
      HandleMarketBookGet(params, result);
   else if(cmd == "market_book_release")
      HandleMarketBookRelease(params, result);
   else if(cmd == "orders_total")
      HandleOrdersTotal(params, result);
   else if(cmd == "orders_get")
      HandleOrdersGet(params, result);
   else if(cmd == "positions_total")
      HandlePositionsTotal(params, result);
   else if(cmd == "positions_get")
      HandlePositionsGet(params, result);
   else if(cmd == "history_orders_total")
      HandleHistoryOrdersTotal(params, result);
   else if(cmd == "history_orders_get")
      HandleHistoryOrdersGet(params, result);
   else if(cmd == "history_deals_total")
      HandleHistoryDealsTotal(params, result);
   else if(cmd == "history_deals_get")
      HandleHistoryDealsGet(params, result);
   else if(cmd == "order_calc_margin")
      HandleOrderCalcMargin(params, result);
   else if(cmd == "order_calc_profit")
      HandleOrderCalcProfit(params, result);
   else if(cmd == "order_send")
      HandleOrderSend(params, result);
   else if(cmd == "order_calc_check" || cmd == "order_check")
      HandleOrderCheck(params, result);
   else if(cmd == "copy_ticks_from")
      HandleCopyTicksFrom(params, result);
   else if(cmd == "copy_ticks_range")
      HandleCopyTicksRange(params, result);
   else if(cmd == "copy_rates_from")
      HandleCopyRatesFrom(params, result);
   else if(cmd == "copy_rates_range")
      HandleCopyRatesRange(params, result);
   else
   {
      result["error"] = "Unknown command";
      result["error_code"] = -7;
   }

   // Serialize and send response
   string response = result.Serialize();
   SendResponse(clientIdx, response);
}

//+------------------------------------------------------------------+
//| Send response to client                                          |
//+------------------------------------------------------------------+
void SendResponse(int clientIdx, string response)
{
   if(clientIdx >= ArraySize(ClientSockets) || ClientSockets[clientIdx] == NULL)
      return;

   // Format: [4-byte length][JSON]
   int len = StringLen(response);
   char lenBuf[4];
   lenBuf[0] = (char)(len & 0xFF);
   lenBuf[1] = (char)((len >> 8) & 0xFF);
   lenBuf[2] = (char)((len >> 16) & 0xFF);
   lenBuf[3] = (char)((len >> 24) & 0xFF);

   ClientSockets[clientIdx].Send(lenBuf, 4, 0);
   ClientSockets[clientIdx].Send(StringToCharArray(response), len, 0);
}

//+------------------------------------------------------------------+
//| Command Handlers                                                  |
//+------------------------------------------------------------------+

void HandleInitialize(CJAVal& params, CJAVal& result)
{
   int login = params["login"].ToInt();
   string password = params["password"].ToStr();
   string server = params["server"].ToStr();

   // MT5 must already be running with an account
   // This command mainly establishes the connection
   result["result"]["success"] = true;
   result["result"]["terminal_path"] = TerminalInfoString(TERMINAL_PATH);
}

void HandleShutdown(CJAVal& params, CJAVal& result)
{
   result["result"]["success"] = true;
}

void HandleVersion(CJAVal& params, CJAVal& result)
{
   result["result"]["version"] = "5.0";
   result["result"]["build"] = (int)TerminalInfoInteger(TERMINAL_BUILD);
   result["result"]["date"] = (datetime)TerminalInfoInteger(TERMINAL_BUILD_DATE);
}

void HandleTerminalInfo(CJAVal& params, CJAVal& result)
{
   result["result"]["community_account"] = (bool)TerminalInfoInteger(TERMINAL_COMMUNITY_ACCOUNT);
   result["result"]["community_connection"] = (bool)TerminalInfoInteger(TERMINAL_COMMUNITY_CONNECTION);
   result["result"]["connected"] = (bool)TerminalInfoInteger(TERMINAL_CONNECTED);
   result["result"]["dlls_allowed"] = (bool)TerminalInfoInteger(TERMINAL_DLLS_ALLOWED);
   result["result"]["trade_allowed"] = (bool)TerminalInfoInteger(TERMINAL_TRADE_ALLOWED);
   result["result"]["name"] = TerminalInfoString(TERMINAL_NAME);
   result["result"]["path"] = TerminalInfoString(TERMINAL_PATH);
   result["result"]["data_path"] = TerminalInfoString(TERMINAL_DATA_PATH);
   result["result"]["common_data_path"] = TerminalInfoString(TERMINAL_COMMONDATA_PATH);
   result["result"]["language"] = TerminalInfoString(TERMINAL_LANGUAGE);
}

void HandleSymbolsTotal(CJAVal& params, CJAVal& result)
{
   result["result"]["total"] = SymbolsTotal(false);
}

void HandleSymbolsGet(CJAVal& params, CJAVal& result)
{
   string group = params["group"].ToStr();
   int total = SymbolsTotal(false);

   for(int i = 0; i < total; i++)
   {
      string name = SymbolName(i, false);
      if(StringLen(group) == 0 || StringFind(name, group) >= 0)
      {
         int idx = result["result"]["symbols"].Size();
         result["result"]["symbols"][idx] = name;
      }
   }
}

void HandleSymbolInfo(CJAVal& params, CJAVal& result)
{
   string symbol = params["symbol"].ToStr();
   if(!SymbolSelect(symbol, true))
   {
      result["error"] = "Symbol not found";
      result["error_code"] = -4;
      return;
   }

   result["result"]["name"] = symbol;
   result["result"]["path"] = SymbolInfoString(symbol, SYMBOL_PATH);
   result["result"]["description"] = SymbolInfoString(symbol, SYMBOL_DESCRIPTION);
   result["result"]["currency_base"] = SymbolInfoString(symbol, SYMBOL_CURRENCY_BASE);
   result["result"]["currency_profit"] = SymbolInfoString(symbol, SYMBOL_CURRENCY_PROFIT);
   result["result"]["currency_margin"] = SymbolInfoString(symbol, SYMBOL_CURRENCY_MARGIN);
   result["result"]["digits"] = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
   result["result"]["trade_mode"] = (int)SymbolInfoInteger(symbol, SYMBOL_TRADE_MODE);
   result["result"]["volume_min"] = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
   result["result"]["volume_max"] = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MAX);
   result["result"]["volume_step"] = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);
   result["result"]["point"] = SymbolInfoDouble(symbol, SYMBOL_POINT);
   result["result"]["bid"] = SymbolInfoDouble(symbol, SYMBOL_BID);
   result["result"]["ask"] = SymbolInfoDouble(symbol, SYMBOL_ASK);
}

void HandleSymbolInfoTick(CJAVal& params, CJAVal& result)
{
   string symbol = params["symbol"].ToStr();
   MqlTick tick;

   if(!SymbolInfoTick(symbol, tick))
   {
      result["error"] = "Failed to get tick";
      result["error_code"] = -1;
      return;
   }

   result["result"]["time"] = (datetime)tick.time;
   result["result"]["bid"] = tick.bid;
   result["result"]["ask"] = tick.ask;
   result["result"]["last"] = tick.last;
   result["result"]["volume"] = (long)tick.volume;
   result["result"]["time_msc"] = tick.time_msc;
   result["result"]["flags"] = tick.flags;
   result["result"]["volume_real"] = tick.volume_real;
}

void HandleSymbolSelect(CJAVal& params, CJAVal& result)
{
   string symbol = params["symbol"].ToStr();
   bool enable = params["enable"].ToBool();
   result["result"]["success"] = SymbolSelect(symbol, enable);
}

void HandleMarketBookAdd(CJAVal& params, CJAVal& result)
{
   string symbol = params["symbol"].ToStr();
   result["result"]["success"] = MarketBookAdd(symbol);
}

void HandleMarketBookGet(CJAVal& params, CJAVal& result)
{
   string symbol = params["symbol"].ToStr();
   MqlBookInfo book[];

   if(!MarketBookGet(symbol, book))
   {
      result["error"] = "Failed to get market book";
      return;
   }

   int size = ArraySize(book);
   for(int i = 0; i < size; i++)
   {
      result["result"]["books"][i]["type"] = book[i].type;
      result["result"]["books"][i]["price"] = book[i].price;
      result["result"]["books"][i]["volume"] = (long)book[i].volume;
      result["result"]["books"][i]["volume_real"] = book[i].volume_real;
   }
}

void HandleMarketBookRelease(CJAVal& params, CJAVal& result)
{
   string symbol = params["symbol"].ToStr();
   result["result"]["success"] = MarketBookRelease(symbol);
}

void HandleOrdersTotal(CJAVal& params, CJAVal& result)
{
   result["result"]["total"] = OrdersTotal();
}

void HandleOrdersGet(CJAVal& params, CJAVal& result)
{
   string group = params["group"].ToStr();
   ulong ticket = (ulong)params["ticket"].ToInt();
   string symbol = params["symbol"].ToStr();

   // Build selection criteria
   if(ticket > 0)
   {
      if(!OrderSelect(ticket))
         return;

      int idx = 0;
      result["result"]["orders"][idx]["ticket"] = (long)OrderGetInteger(ORDER_TICKET);
      result["result"]["orders"][idx]["symbol"] = OrderGetString(ORDER_SYMBOL);
      result["result"]["orders"][idx]["type"] = (int)OrderGetInteger(ORDER_TYPE);
      result["result"]["orders"][idx]["volume_current"] = OrderGetDouble(ORDER_VOLUME_CURRENT);
      result["result"]["orders"][idx]["price_open"] = OrderGetDouble(ORDER_PRICE_OPEN);
      result["result"]["orders"][idx]["sl"] = OrderGetDouble(ORDER_SL);
      result["result"]["orders"][idx]["tp"] = OrderGetDouble(ORDER_TP);
      return;
   }

   int total = OrdersTotal();
   for(int i = 0; i < total; i++)
   {
      ulong t = OrderGetTicket(i);
      if(t == 0) continue;

      string sym = OrderGetString(ORDER_SYMBOL);
      if(StringLen(symbol) > 0 && sym != symbol) continue;
      if(StringLen(group) > 0 && StringFind(sym, group) < 0) continue;

      int idx = result["result"]["orders"].Size();
      result["result"]["orders"][idx]["ticket"] = (long)t;
      result["result"]["orders"][idx]["symbol"] = sym;
      result["result"]["orders"][idx]["type"] = (int)OrderGetInteger(ORDER_TYPE);
      result["result"]["orders"][idx]["volume_current"] = OrderGetDouble(ORDER_VOLUME_CURRENT);
      result["result"]["orders"][idx]["price_open"] = OrderGetDouble(ORDER_PRICE_OPEN);
      result["result"]["orders"][idx]["sl"] = OrderGetDouble(ORDER_SL);
      result["result"]["orders"][idx]["tp"] = OrderGetDouble(ORDER_TP);
   }
}

void HandlePositionsTotal(CJAVal& params, CJAVal& result)
{
   result["result"]["total"] = PositionsTotal();
}

void HandlePositionsGet(CJAVal& params, CJAVal& result)
{
   string group = params["group"].ToStr();
   ulong ticket = (ulong)params["ticket"].ToInt();
   string symbol = params["symbol"].ToStr();

   // Build selection criteria
   if(ticket > 0)
   {
      if(!PositionSelectByTicket(ticket))
         return;

      int idx = 0;
      result["result"]["positions"][idx]["ticket"] = (long)PositionGetInteger(POSITION_TICKET);
      result["result"]["positions"][idx]["symbol"] = PositionGetString(POSITION_SYMBOL);
      result["result"]["positions"][idx]["type"] = (int)PositionGetInteger(POSITION_TYPE);
      result["result"]["positions"][idx]["volume"] = PositionGetDouble(POSITION_VOLUME);
      result["result"]["positions"][idx]["price_open"] = PositionGetDouble(POSITION_PRICE_OPEN);
      result["result"]["positions"][idx]["sl"] = PositionGetDouble(POSITION_SL);
      result["result"]["positions"][idx]["tp"] = PositionGetDouble(POSITION_TP);
      result["result"]["positions"][idx]["profit"] = PositionGetDouble(POSITION_PROFIT);
      return;
   }

   int total = PositionsTotal();
   for(int i = 0; i < total; i++)
   {
      string sym = PositionGetSymbol(i);
      if(StringLen(sym) == 0) continue;
      if(StringLen(symbol) > 0 && sym != symbol) continue;
      if(StringLen(group) > 0 && StringFind(sym, group) < 0) continue;

      int idx = result["result"]["positions"].Size();
      result["result"]["positions"][idx]["ticket"] = (long)PositionGetInteger(POSITION_TICKET);
      result["result"]["positions"][idx]["symbol"] = sym;
      result["result"]["positions"][idx]["type"] = (int)PositionGetInteger(POSITION_TYPE);
      result["result"]["positions"][idx]["volume"] = PositionGetDouble(POSITION_VOLUME);
      result["result"]["positions"][idx]["price_open"] = PositionGetDouble(POSITION_PRICE_OPEN);
      result["result"]["positions"][idx]["sl"] = PositionGetDouble(POSITION_SL);
      result["result"]["positions"][idx]["tp"] = PositionGetDouble(POSITION_TP);
      result["result"]["positions"][idx]["profit"] = PositionGetDouble(POSITION_PROFIT);
   }
}

void HandleHistoryOrdersTotal(CJAVal& params, CJAVal& result)
{
   datetime from = (datetime)params["from_date"].ToInt();
   datetime to = (datetime)params["to_date"].ToInt();
   result["result"]["total"] = HistoryOrdersTotal(from, to);
}

void HandleHistoryOrdersGet(CJAVal& params, CJAVal& result)
{
   datetime from = (datetime)params["from_date"].ToInt();
   datetime to = (datetime)params["to_date"].ToInt();
   string group = params["group"].ToStr();

   if(HistoryOrdersTotal(from, to) > 0)
   {
      for(int i = 0; i < HistoryDealsTotal(); i++)
      {
         ulong ticket = HistoryDealGetTicket(i);
         if(ticket == 0) continue;

         int idx = result["result"]["orders"].Size();
         result["result"]["orders"][idx]["ticket"] = (long)ticket;
         result["result"]["orders"][idx]["symbol"] = HistoryDealGetString(ticket, DEAL_SYMBOL);
      }
   }
}

void HandleHistoryDealsTotal(CJAVal& params, CJAVal& result)
{
   datetime from = (datetime)params["from_date"].ToInt();
   datetime to = (datetime)params["to_date"].ToInt();
   result["result"]["total"] = HistoryDealsTotal(from, to);
}

void HandleHistoryDealsGet(CJAVal& params, CJAVal& result)
{
   datetime from = (datetime)params["from_date"].ToInt();
   datetime to = (datetime)params["to_date"].ToInt();

   if(HistoryDealsTotal(from, to) > 0)
   {
      for(int i = 0; i < HistoryDealsTotal(); i++)
      {
         ulong ticket = HistoryDealGetTicket(i);
         if(ticket == 0) continue;

         int idx = result["result"]["deals"].Size();
         result["result"]["deals"][idx]["ticket"] = (long)ticket;
         result["result"]["deals"][idx]["symbol"] = HistoryDealGetString(ticket, DEAL_SYMBOL);
         result["result"]["deals"][idx]["type"] = (int)HistoryDealGetInteger(ticket, DEAL_TYPE);
         result["result"]["deals"][idx]["volume"] = HistoryDealGetDouble(ticket, DEAL_VOLUME);
         result["result"]["deals"][idx]["price"] = HistoryDealGetDouble(ticket, DEAL_PRICE);
      }
   }
}

void HandleOrderCalcMargin(CJAVal& params, CJAVal& result)
{
   ENUM_ORDER_TYPE action = (ENUM_ORDER_TYPE)params["action"].ToInt();
   string symbol = params["symbol"].ToStr();
   double volume = params["volume"].ToDbl();
   double price = params["price"].ToDbl();

   double margin;
   if(OrderCalcMargin(action, symbol, volume, price, margin))
   {
      result["result"]["margin"] = margin;
   }
   else
   {
      result["error"] = "Failed to calculate margin";
      result["error_code"] = -1;
   }
}

void HandleOrderCalcProfit(CJAVal& params, CJAVal& result)
{
   ENUM_ORDER_TYPE action = (ENUM_ORDER_TYPE)params["action"].ToInt();
   string symbol = params["symbol"].ToStr();
   double volume = params["volume"].ToDbl();
   double price_open = params["price_open"].ToDbl();
   double price_close = params["price_close"].ToDbl();

   double profit;
   if(OrderCalcProfit(action, symbol, volume, price_open, price_close, profit))
   {
      result["result"]["profit"] = profit;
   }
   else
   {
      result["error"] = "Failed to calculate profit";
      result["error_code"] = -1;
   }
}

void HandleOrderSend(CJAVal& params, CJAVal& result)
{
   CJAVal req = params["request"];
   MqlTradeRequest request = {};
   MqlTradeResult tradeResult = {};

   request.action = (ENUM_TRADE_REQUEST_ACTIONS)req["action"].ToInt();
   request.symbol = req["symbol"].ToStr();
   request.volume = req["volume"].ToDbl();
   request.type = (ENUM_ORDER_TYPE)req["type"].ToInt();
   request.price = req["price"].ToDbl();
   request.deviation = req["deviation"].ToInt();

   if(req["sl"].ToDbl() > 0)
      request.sl = req["sl"].ToDbl();
   if(req["tp"].ToDbl() > 0)
      request.tp = req["tp"].ToDbl();
   if(StringLen(req["comment"].ToStr()) > 0)
      request.comment = req["comment"].ToStr();
   if(req["magic"].ToInt() > 0)
      request.magic = req["magic"].ToInt();

   if(!OrderSend(request, tradeResult))
   {
      result["error"] = "OrderSend failed";
      result["error_code"] = -1;
      return;
   }

   result["result"]["retcode"] = (int)tradeResult.retcode;
   result["result"]["deal"] = (long)tradeResult.deal;
   result["result"]["order"] = (long)tradeResult.order;
   result["result"]["volume"] = tradeResult.volume;
   result["result"]["price"] = tradeResult.price;
   result["result"]["bid"] = tradeResult.bid;
   result["result"]["ask"] = tradeResult.ask;
   result["result"]["comment"] = tradeResult.comment;
}

void HandleOrderCheck(CJAVal& params, CJAVal& result)
{
   CJAVal req = params["request"];
   MqlTradeRequest request = {};
   MqlTradeCheckResult checkResult = {};

   request.action = (ENUM_TRADE_REQUEST_ACTIONS)req["action"].ToInt();
   request.symbol = req["symbol"].ToStr();
   request.volume = req["volume"].ToDbl();
   request.type = (ENUM_ORDER_TYPE)req["type"].ToInt();
   request.price = req["price"].ToDbl();

   if(!OrderCheck(request, checkResult))
   {
      result["error"] = "OrderCheck failed";
      result["error_code"] = -1;
      return;
   }

   result["result"]["retcode"] = (int)checkResult.retcode;
   result["result"]["balance"] = checkResult.balance;
   result["result"]["equity"] = checkResult.equity;
   result["result"]["profit"] = checkResult.profit;
   result["result"]["margin"] = checkResult.margin;
   result["result"]["margin_free"] = checkResult.margin_free;
   result["result"]["margin_level"] = checkResult.margin_level;
}

void HandleCopyTicksFrom(CJAVal& params, CJAVal& result)
{
   string symbol = params["symbol"].ToStr();
   datetime from = (datetime)params["date_from"].ToInt();
   int count = params["count"].ToInt();
   uint flags = COPY_TICKS_ALL;

   MqlTick ticks[];
   int copied = CopyTicks(symbol, ticks, flags, from, count);

   if(copied > 0)
   {
      for(int i = 0; i < copied; i++)
      {
         result["result"]["ticks"][i]["time"] = (datetime)ticks[i].time;
         result["result"]["ticks"][i]["bid"] = ticks[i].bid;
         result["result"]["ticks"][i]["ask"] = ticks[i].ask;
         result["result"]["ticks"][i]["last"] = ticks[i].last;
         result["result"]["ticks"][i]["volume"] = (long)ticks[i].volume;
         result["result"]["ticks"][i]["time_msc"] = ticks[i].time_msc;
         result["result"]["ticks"][i]["flags"] = ticks[i].flags;
         result["result"]["ticks"][i]["volume_real"] = ticks[i].volume_real;
      }
   }
}

void HandleCopyTicksRange(CJAVal& params, CJAVal& result)
{
   string symbol = params["symbol"].ToStr();
   datetime from = (datetime)params["date_from"].ToInt();
   datetime to = (datetime)params["date_to"].ToInt();
   uint flags = COPY_TICKS_ALL;

   MqlTick ticks[];
   int copied = CopyTicksRange(symbol, ticks, flags, from, to);

   if(copied > 0)
   {
      for(int i = 0; i < copied; i++)
      {
         result["result"]["ticks"][i]["time"] = (datetime)ticks[i].time;
         result["result"]["ticks"][i]["bid"] = ticks[i].bid;
         result["result"]["ticks"][i]["ask"] = ticks[i].ask;
         result["result"]["ticks"][i]["last"] = ticks[i].last;
         result["result"]["ticks"][i]["volume"] = (long)ticks[i].volume;
         result["result"]["ticks"][i]["time_msc"] = ticks[i].time_msc;
         result["result"]["ticks"][i]["flags"] = ticks[i].flags;
         result["result"]["ticks"][i]["volume_real"] = ticks[i].volume_real;
      }
   }
}

void HandleCopyRatesFrom(CJAVal& params, CJAVal& result)
{
   string symbol = params["symbol"].ToStr();
   ENUM_TIMEFRAMES timeframe = (ENUM_TIMEFRAMES)params["timeframe"].ToInt();
   datetime from = (datetime)params["date_from"].ToInt();
   int count = params["count"].ToInt();

   MqlRates rates[];
   int copied = CopyRates(symbol, timeframe, from, count, rates);

   if(copied > 0)
   {
      for(int i = 0; i < copied; i++)
      {
         result["result"]["rates"][i]["time"] = (datetime)rates[i].time;
         result["result"]["rates"][i]["open"] = rates[i].open;
         result["result"]["rates"][i]["high"] = rates[i].high;
         result["result"]["rates"][i]["low"] = rates[i].low;
         result["result"]["rates"][i]["close"] = rates[i].close;
         result["result"]["rates"][i]["tick_volume"] = (long)rates[i].tick_volume;
         result["result"]["rates"][i]["spread"] = rates[i].spread;
         result["result"]["rates"][i]["real_volume"] = (long)rates[i].real_volume;
      }
   }
}

void HandleCopyRatesRange(CJAVal& params, CJAVal& result)
{
   string symbol = params["symbol"].ToStr();
   ENUM_TIMEFRAMES timeframe = (ENUM_TIMEFRAMES)params["timeframe"].ToInt();
   datetime from = (datetime)params["date_from"].ToInt();
   datetime to = (datetime)params["date_to"].ToInt();

   MqlRates rates[];
   int copied = CopyRates(symbol, timeframe, from, to, rates);

   if(copied > 0)
   {
      for(int i = 0; i < copied; i++)
      {
         result["result"]["rates"][i]["time"] = (datetime)rates[i].time;
         result["result"]["rates"][i]["open"] = rates[i].open;
         result["result"]["rates"][i]["high"] = rates[i].high;
         result["result"]["rates"][i]["low"] = rates[i].low;
         result["result"]["rates"][i]["close"] = rates[i].close;
         result["result"]["rates"][i]["tick_volume"] = (long)rates[i].tick_volume;
         result["result"]["rates"][i]["spread"] = rates[i].spread;
         result["result"]["rates"][i]["real_volume"] = (long)rates[i].real_volume;
      }
   }
}
