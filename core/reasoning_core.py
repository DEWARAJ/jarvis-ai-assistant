"""Reasoning Core: intent classification + lightweight task decomposition.

Transparent rule-based matching (no external LLM). Commands fire only when the message
STARTS with a known phrase (after stripping wake-words like 'Jarvis'); everything else
falls through to the LLM. First matching rule wins, so order matters.
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field


@dataclass
class Intent:
    name: str
    agent: str | None = None
    args: str = ""
    confidence: float = 0.0
    plan: list = field(default_factory=list)


_RULES = [
    (("shutdown jarvis", "shut down jarvis", "exit", "quit"), "shutdown", None),
    (("help", "commands"), "help", None),
    # ---- smart-trader bot control (high precedence so 'backtest'/'signals' don't fall to web search) ----
    (("stop paper trading", "stop the paper trade", "halt paper trading", "stop trading bot", "stop the bot"), "bot_paper_stop", None),
    (("start paper trading", "begin paper trading", "run paper trading", "start the trading bot", "go live on paper", "paper trade"), "bot_paper_start", None),
    (("paper trading status", "is the bot trading", "is paper trading running", "bot status", "trading bot status"), "bot_paper_status", None),
    (("run a backtest", "run backtest", "backtest the", "backtest for", "backtest"), "bot_backtest", None),
    (("walk forward", "walkforward", "walk-forward", "validate the strategy", "out of sample test"), "bot_walkforward", None),
    (("trading pnl", "trade log", "trading performance", "bot pnl", "show pnl", "win rate", "how is the bot doing", "how's the bot doing"), "bot_pnl", None),
    (("trading signals", "trade signals", "scan the market", "bot signals", "any setups", "trading recommendations", "scan for trades", "check signals"), "bot_signals", None),
    (("run without claude", "run without cloud", "run without the cloud", "run without internet", "run without a cloud brain"), "local_brain", None),
    # ---- self-code rewrite + live screen watch + work suggestions (high precedence) ----
    (("rewrite your code", "modify your code", "edit your code", "change your code", "rewrite your source", "modify your source", "edit your source", "rewrite yourself", "modify yourself", "edit yourself", "rewrite your own code", "upgrade your code", "upgrade your core", "upgrade your own code", "self upgrade", "self-upgrade", "modify your core", "edit your core", "rewrite your core", "change your core", "patch your code", "patch yourself", "improve your code", "fix your code", "rewrite core/", "modify core/", "upgrade core/", "edit core/", "rewrite tools/", "rewrite agents/", "rewrite channels/", "modify tools/", "modify agents/", "modify channels/"), "self_code", None),
    (("stop watching my screen", "stop watching my work", "stop watching me", "stop the screen watch", "stop screen watch"), "screen_watch_off", None),
    (("watch my screen", "watch my work", "watch what i'm doing", "watch what i am doing", "keep an eye on my screen", "keep an eye on my work", "suggest as i work", "see what i'm doing", "look at what i'm doing", "watch over my work"), "screen_watch_on", None),
    (("suggest on this", "what should i do here", "any suggestions on my work", "suggestions on this", "what do you suggest here", "help me with this task", "advise on what i'm doing", "give me suggestions on my work", "suggestions for my work"), "suggest_now", None),
    # ---- daily workflows (Upgrade 6): high precedence, distinctive phrases ----
    (("start my day", "start the day", "begin my day", "start my morning", "morning routine", "run my morning routine", "kick off my day"), "wf_start_day", None),
    (("wind down", "end my day", "end of day", "wrap up my day", "wrap up the day", "evening routine", "close out my day"), "wf_wind_down", None),
    (("deep work", "focus mode", "help me focus", "time to focus", "lock in", "focus session", "focus on"), "wf_focus", None),
    (("research brief on", "research brief", "save a brief on", "write a brief on", "write me a brief on", "prepare a brief on", "brief and save"), "wf_research_brief", None),
    (("system test", "self test", "run diagnostics", "diagnostics", "test the system", "run a self test"), "self_test", None),
    (("self eval", "self evaluation", "self-eval", "run self eval", "reliability report", "grade yourself", "score yourself", "evaluate yourself", "run a self evaluation"), "self_eval", None),
    (("fix yourself", "repair yourself", "self heal", "heal yourself", "self repair", "self-heal", "fix your problems", "fix any problems"), "self_heal", None),
    (("check for updates", "check updates", "update yourself", "upgrade yourself", "pull updates", "self update", "update from the internet", "upgrade from the internet"), "check_updates", None),
    (("improve yourself", "self improve", "develop yourself", "make yourself better", "how can you get better", "upgrade your skills", "self improvement", "better yourself", "evolve yourself"), "self_improve", None),
    # ---- Council: convene the multi-agent review board ----
    (("council", "convene the council", "convene council", "council review", "ask the council", "council on", "review with the council", "full council"), "council_review", None),
    # ---- Phase 5: deep verification debate for high-stakes / consequential calls ----
    (("deep verify", "verify this decision", "stress test this", "stress test my decision", "run a full verification", "verification council", "pressure test this", "pressure-test this"), "deep_verify", None),
    # ---- Proactive Advisor (unprompted suggestions) ----
    (("proactive status", "proactive advice status", "are you watching", "advisor status"), "proactive_status", None),
    (("proactive off", "proactive advice off", "stop advising me", "stop suggestions", "turn off proactive", "advisor off", "stop proactive", "be quiet unless i ask"), "proactive_off", None),
    (("proactive on", "proactive advice on", "proactive mode", "give me proactive advice", "watch and advise me", "advise me proactively", "turn on proactive", "advisor on", "speak up when useful", "be my companion"), "proactive_on", None),
    # ---- Current-tab browser control (BEFORE generic open/click/read so they win) ----
    (("read this page", "read this tab", "read the current tab", "read current tab", "read the page i'm on", "read the page im on", "what does this page say", "what's on this page", "whats on this page", "summarize this page", "summarise this page", "read this website"), "browser_read", None),
    (("choose the option", "select the option", "choose option", "select option", "pick the option", "choose from the dropdown", "select from the dropdown", "choose", "select"), "browser_select_option", None),
    (("click the link", "open the link", "click link", "open link on this tab", "on this tab click", "click the link that says", "open the link on this tab", "open the link on current tab", "click on this tab"), "browser_click_link", None),
    # ---- Iron Man Mode: continuous self-driving autonomy (status/off BEFORE on so they win) ----
    (("iron man status", "iron man mode status", "autonomy status", "how is iron man", "is iron man on", "how's iron man"), "iron_man_status", None),
    (("iron man mode off", "iron man off", "disengage iron man", "stop iron man", "turn off iron man", "exit iron man", "stand down", "iron man stand down"), "iron_man_off", None),
    (("iron man mode on", "iron man mode", "iron man on", "engage iron man", "go iron man", "activate iron man", "turn on iron man", "enable iron man", "iron man"), "iron_man_on", None),
    (("show goals", "list goals", "my goals", "show my goals", "goal list", "what goals", "autonomy goals", "what are my goals", "show the goals"), "goals_list", None),
    (("add goal", "add a goal", "queue goal", "queue a goal", "new goal", "set a goal", "set goal", "give yourself a goal", "add the goal", "pursue this goal", "work on goal"), "goal_add", None),
    # ---- Mission Control: continuous autonomy (status/resume/abort BEFORE start so they win) ----
    (("mission status", "how is the mission", "how's the mission", "mission progress"), "mission_status", None),
    (("continue mission", "resume mission", "resume the mission", "continue the mission", "keep going on the mission"), "mission_resume", None),
    (("abort mission", "stop mission", "cancel mission", "end mission", "halt mission"), "mission_abort", None),
    (("mission", "start a mission", "start mission", "run a mission", "go fully autonomous", "full autonomy on", "go autonomous on", "autonomous mission", "take on the mission"), "mission_start", None),
    # ---- live skill install / upgrade (download order matters; "from" -> download) ----
    (("install the autonomous toolkit", "autonomous toolkit", "install autonomous toolkit", "install the full toolkit", "full toolkit", "the full toolkit", "skill up", "download all skills", "download all the skills", "install all skills", "install all the skills", "install all tools", "load all skills", "get all skills", "get all the skills", "install everything", "equip yourself", "become a top agent", "make yourself a top agent", "top agent toolkit", "power yourself up"), "toolkit_install", None),
    (("download skill from", "add skill from", "install skill from", "download from", "get skill from"), "skill_download", None),
    (("upgrade skill", "upgrade package", "update package", "upgrade the package", "update the package", "upgrade", "update"), "skill_upgrade", None),
    (("show skills", "installed skills", "list skills", "my skills", "what skills do you have", "what can you install"), "skills_list", None),
    (("deepen the", "deepen my", "deepen", "go deeper on", "go deeper", "learn more about", "study more about", "dig deeper into"), "deepen_skill", None),
    (("learn the", "learn how to", "learn about", "teach yourself", "teach your self", "master the", "study the", "become an expert in", "become expert in", "acquire the skill", "learn", "master", "study"), "learn_skill", None),
    (("install the skill", "install skill", "download skill", "add skill", "get the skill", "install package", "pip install", "add the capability", "give yourself the", "install"), "skill_install", None),
    (("doctor", "health check", "full system check", "full check", "run a health check", "are you healthy", "diagnose yourself", "self diagnostic", "self-diagnostic", "are you okay", "are you ok"), "doctor", None),
    (("run system check", "system check", "capability check", "check capabilities", "what can you do on this pc"), "system_check", None),
    # ---- Hermes Agent delegation (code-variant first so build/fix wins over generic run) ----
    (("ask hermes to build", "ask hermes to code", "ask hermes to fix", "have hermes build", "have hermes code", "have hermes fix", "tell hermes to build", "hermes build", "hermes code", "hermes fix"), "hermes_code", None),
    (("delegate to hermes", "ask hermes to", "ask hermes", "have hermes", "tell hermes to", "tell hermes", "use hermes to", "use hermes", "hey hermes", "ok hermes", "hermes"), "hermes_run", None),
    (("write code", "write a script", "write a program", "write me a script", "write a python", "generate code", "code a", "create a script"), "write_code", None),
    (("run command", "execute command", "run in terminal", "terminal command", "execute", "run the command", "run"), "run_command", None),
    (("verify on screen", "verify the screen", "check the screen", "look and verify", "confirm on screen", "is it on screen", "did it work", "check if it worked", "verify"), "verify_screen", None),
    (("what is on my screen", "whats on my screen", "what's on my screen", "look at my screen", "read my screen", "see my screen", "describe my screen", "what do you see", "look at the screen", "see whats on screen"), "see_screen", None),
    (("click the first result", "click first result", "open the first result", "play the first result", "play first result"), "click_first", None),
    (("play the second", "play the third", "play the fourth", "play the fifth", "play the 2nd", "play the 3rd", "play the 4th", "play result", "play the next", "play video number", "play number"), "play_nth", None),
    (("play song", "play the song", "play"), "youtube_play", None),
    (("pause the video", "pause video", "pause"), "media_pause", None),
    (("resume the video", "resume video", "unpause", "resume"), "media_resume", None),
    (("increase volume", "volume up", "turn up the volume", "turn up volume", "raise volume", "louder"), "volume_up", None),
    (("decrease volume", "volume down", "turn down the volume", "turn down volume", "lower the volume", "lower volume", "quieter"), "volume_down", None),
    (("unmute volume", "unmute the volume", "unmute"), "volume_unmute", None),
    (("mute volume", "mute the volume", "mute", "silence"), "volume_mute", None),
    (("list tabs", "show tabs", "what tabs are open", "show my tabs", "show open tabs", "what's open in chrome", "whats open in chrome", "how many tabs", "my open tabs"), "list_tabs", None),
    (("close tab", "close the tab", "close this tab", "close current tab", "close the current tab", "close the browser tab"), "close_tab", None),
    (("force close", "kill", "close the app", "close app", "close window", "close the window", "close"), "close_app", None),
    (("type", "type out", "write out", "type this"), "input_type", None),
    (("press", "hit", "key"), "input_press", None),
    (("right click", "right-click", "context menu"), "right_click", None),
    (("move mouse to", "move the cursor to", "move cursor to", "move the mouse to"), "move_mouse", None),
    (("click at", "click on coordinates", "click position"), "click_at", None),
    (("click the", "click on", "tap the", "tap on", "click button", "click the link", "click the icon", "click where it says", "vision click"), "click_vision", None),
    (("double click", "click"), "input_click", None),
    (("sleep the system", "sleep the computer", "sleep my computer", "sleep my pc", "sleep the pc", "put the computer to sleep", "put my computer to sleep", "sleep system", "hibernate"), "power_sleep", None),
    (("lock the system", "lock system", "lock my pc", "lock the pc", "lock the computer", "lock my computer", "lock the screen", "lock my screen", "lock screen"), "power_lock", None),
    (("restart confirmed", "restart the computer", "restart system", "restart my computer", "reboot", "restart"), "power_restart", None),
    (("shutdown confirmed", "shut down the computer", "shutdown the computer", "turn off the computer", "shut down", "shutdown"), "power_shutdown", None),
    (("take a screenshot", "take screenshot", "screenshot", "capture screen", "screen shot", "grab the screen"), "screenshot", None),
    (("enable debug mode", "debug mode on", "debug on", "turn on debug"), "debug_on", None),
    (("disable debug mode", "debug mode off", "debug off", "turn off debug"), "debug_off", None),
    (("open google and search", "search google for", "google search", "google for", "google"), "browser_google", None),
    (("open youtube and search", "search youtube for", "youtube search", "youtube"), "browser_youtube", None),
    (("search amazon for", "amazon search", "amazon"), "browser_amazon", None),
    (("google maps", "search maps for", "maps for", "directions to"), "browser_maps", None),
    (("search the web", "search online", "web search", "search for", "look up online", "find out about", "search the internet"), "research", None),
    (("search", "look up"), "browser_google", None),
    (("open website", "open site", "visit"), "open_site", None),
    (("scroll to the bottom", "scroll to bottom", "go to the bottom", "jump to bottom", "scroll all the way down"), "scroll_bottom", None),
    (("scroll to the top", "scroll to top", "go to the top", "jump to top", "scroll all the way up"), "scroll_top", None),
    (("scroll down", "scroll the page down", "scroll down the page", "page down", "scroll a bit down"), "scroll_down", None),
    (("scroll up", "scroll the page up", "scroll up the page", "page up", "scroll a bit up"), "scroll_up", None),
    (("go forward", "forward", "next page"), "go_forward", None),
    (("go back", "back", "previous page", "navigate back"), "browser_back", None),
    (("refresh", "reload", "refresh the page", "reload the page"), "browser_refresh", None),
    (("new tab", "open a new tab", "open new tab"), "new_tab", None),
    (("previous tab", "switch to previous tab", "go to previous tab"), "prev_tab", None),
    (("switch tab", "next tab", "switch to next tab", "switch to the next tab"), "switch_tab", None),
    (("reopen tab", "reopen closed tab", "reopen the tab", "reopen last tab"), "reopen_tab", None),
    (("zoom in", "zoom in the page"), "zoom_in", None),
    (("zoom out", "zoom out the page"), "zoom_out", None),
    (("reset zoom", "actual size", "default zoom"), "zoom_reset", None),
    (("exit full screen", "exit fullscreen", "leave full screen"), "exit_fullscreen", None),
    (("full screen", "fullscreen", "make it full screen", "go full screen"), "fullscreen", None),
    (("stop loading", "stop the page", "stop loading the page"), "stop_loading", None),
    (("turn on captions", "captions on", "turn captions on", "show captions", "turn off captions", "captions off"), "captions", None),
    (("turn on wifi", "turn off wifi", "enable wifi", "disable wifi", "wifi settings", "open wifi settings", "wi-fi", "wifi"), "wifi", None),
    (("turn on bluetooth", "turn off bluetooth", "enable bluetooth", "disable bluetooth", "bluetooth settings", "open bluetooth settings", "bluetooth"), "bluetooth", None),
    # ---- Windows native Settings / Control Panel (BEFORE generic open_app so 'open settings'
    #      opens the OS Settings app, NOT a Chrome web search). arg carries the panel name. ----
    (("open control panel", "control panel"), "open_control_panel", None),
    (("open display settings", "display settings", "screen settings", "open screen settings",
      "open sound settings", "sound settings", "audio settings", "open audio settings",
      "open battery settings", "battery settings", "power settings", "open power settings",
      "sleep settings", "open windows update", "windows update", "check for windows updates",
      "open update settings", "update settings", "open storage settings", "storage settings",
      "open apps settings", "apps settings", "installed apps", "open notification settings",
      "notification settings", "open privacy settings", "privacy settings",
      "open network settings", "network settings", "open personalization settings",
      "personalization settings", "open about settings", "system about", "device info",
      "open settings", "open windows settings", "open system settings", "open the settings",
      "open settings app", "windows settings", "system settings", "pc settings", "settings app",
      "settings"), "open_settings", None),
    (("open", "launch", "start app", "go to"), "open_app", None),
    (("latest news", "latest ai news", "latest crypto news", "latest stock market news", "latest stock news", "latest business news", "latest world news", "latest tech news", "latest market news", "today news", "todays news", "read latest news", "read news", "ai news", "crypto news", "stock market news", "market news", "business news", "world news", "tech news", "news about", "news"), "news", None),
    (("fast mode", "speed mode"), "mode_fast", None),
    (("deep mode", "deep research mode", "deep thinking"), "mode_deep", None),
    (("private mode", "offline mode", "local mode"), "mode_private", None),
    (("market briefing", "market update", "markets today", "market summary", "market brief"), "market_briefing", None),
    # ---- proactive monitoring (Upgrade 5): distinct triggers so bare "watch" still = trading watchlist ----
    (("monitor", "alert me if", "alert me when", "notify me if", "notify me when", "keep an eye on", "keep watch on", "watch news about", "watch news on", "watch the page", "watch the website", "watch website", "watch for changes", "let me know if", "let me know when"), "watch_add", None),
    (("show monitors", "my monitors", "what are you monitoring", "show watches", "what are you watching", "active monitors", "list monitors"), "watches_list", None),
    (("stop monitoring", "stop watching", "unmonitor", "remove monitor", "cancel monitor", "clear monitors", "clear all monitors", "clear watches"), "watch_remove", None),
    (("anything new", "any alerts", "any updates for me", "check my monitors", "check monitors", "check my watches"), "check_now", None),
    (("add to watchlist", "to watchlist", "watch"), "add_watch", None),
    (("show watchlist", "my watchlist", "watchlist"), "show_watchlist", None),
    (("risk reward", "risk/reward", "reward to risk", "risk to reward"), "risk_reward", None),
    (("price of", "price for", "stock price", "crypto price", "price", "quote for", "how much is"), "price", None),
    (("weather", "what is the weather", "whats the weather", "weather today", "weather in", "is it going to rain", "temperature outside"), "weather", None),
    (("traffic to", "traffic", "how is the traffic", "traffic conditions"), "traffic", None),
    (("good morning", "morning jarvis"), "greet_morning", None),
    (("good afternoon",), "greet_afternoon", None),
    (("good evening",), "greet_evening", None),
    (("good night", "goodnight"), "greet_night", None),
    (("daily briefing", "briefing", "brief me"), "daily_briefing", "personal_companion"),
    (("plan my day", "plan day"), "plan_day", "personal_companion"),
    (("evening review", "evening recap"), "evening_review", "personal_companion"),
    (("show tasks", "list tasks", "my tasks"), "show_tasks", None),
    (("create task", "add task", "new task"), "create_task", None),
    (("complete task", "done task", "finish task"), "complete_task", None),
    (("organize", "organise", "tidy up", "tidy", "clean up"), "organize_folder", None),
    (("scan folder", "scan", "list folder", "what is in", "what's in", "whats in"), "scan_folder", None),
    (("read file", "summarize file", "summarise file", "read the file", "summarize the file"), "read_file", None),
    (("delete file", "delete files", "remove file", "delete", "remove"), "delete_files", None),
    (("find file", "search for", "locate file", "find"), "find_files", None),
    # ---- utility: conversion / health / security / fun (sukeesh/jarvis-style practical tools) ----
    (("convert", "how many"), "utility_convert", None),
    (("bmi", "body mass index", "am i overweight", "am i underweight", "my bmi"), "utility_bmi", None),
    (("calorie needs", "calorie requirement", "daily calories", "how many calories do i need", "calorie calculator", "bmr"), "utility_calories", None),
    (("generate a password", "generate password", "create a password", "make a password", "random password", "strong password", "new password"), "utility_password", None),
    (("calculate", "compute", "solve", "evaluate", "math", "calc"), "utility_calc", None),
    (("tell me a joke", "tell a joke", "joke", "make me laugh", "say something funny", "funny"), "utility_joke", None),
    (("translate", "translation", "translate this", "translate to"), "utility_translate", None),
    (("rollback last upgrade", "roll back last upgrade", "rollback the upgrade", "undo last upgrade", "revert last upgrade", "rollback upgrade"), "rollback_upgrade", None),
    (("upgrade history", "self upgrade log", "show upgrade history", "self-upgrade history"), "upgrade_history", None),
    (("confirm", "confirmed", "yes do it", "yes confirm", "go ahead", "do it", "proceed", "execute it", "approve upgrade", "approve the upgrade", "apply the upgrade", "approve it"), "confirm", None),
    (("cancel", "never mind", "nevermind", "forget it", "stop that", "stop", "stop it", "abort", "do not click", "dont click", "stop automation", "halt"), "cancel", None),
    (("read url", "open url", "read the page", "fetch url", "read site", "summarize url"), "read_url", None),
    (("get live data on", "get live data", "live data on", "get the latest data on", "get me live data on", "pull live data on"), "research", None),
    (("research", "look up online", "search the web", "search online", "web search", "search for", "look up", "find out about"), "research", None),
    (("unread email", "unread emails", "new emails", "new mail"), "unread_email", None),
    (("check email", "check my email", "read my email", "read email", "check inbox", "check my inbox", "my inbox"), "check_email", None),
    (("about my business", "my business is", "set business", "remember about my business", "business profile"), "set_business", None),
    (("what did we talk about", "what did we discuss", "what have we discussed", "recall our conversation", "recall our chat", "recall previous conversation", "recall the previous conversation", "our conversation history", "our chat history", "remember our conversation", "do you remember our conversation", "do you remember what we", "search our chats", "search our conversation", "recall our chats about", "what did we talk about regarding"), "convo_recall", None),
    (("forget our conversations", "forget our conversation", "clear chat history", "clear conversation history", "clear our conversation", "delete our conversations", "wipe our chat", "forget our chats"), "convo_forget", None),
    (("what do you know about me", "what do you remember", "what do you know about", "what have you remembered"), "memory_recall", None),
    (("forget about me", "forget what you know", "forget everything about me", "clear your memory"), "memory_forget", None),
    (("remember that", "remember", "note that", "keep in mind", "dont forget", "make a note that"), "memory_remember", None),
    (("business review", "review business"), "business_review", "business_strategy"),
    (("draft customer reply", "customer reply", "reply to customer", "draft reply"), "draft_customer_reply", "customer_support"),
    (("marketing agent for ad hooks", "ad hooks", "ask marketing"), "ad_hooks", "marketing"),
    (("ecommerce agent to improve product page", "improve product page", "ask ecommerce", "product page"), "improve_product_page", "ecommerce"),
    (("create trading journal entry", "trading journal entry", "journal entry"), "trading_journal_entry", "trading_research"),
    (("trading review", "review trading", "trade review"), "trading_review", "trading_research"),
    # ---- autonomous execution + situational briefing (plugin: task-automation / core) ----
    (("handle this end to end", "handle it end to end", "just get it done", "do the whole thing", "take it from here", "take over this", "run with it", "autonomous mode", "handle this", "handle it", "handle the", "handle my", "handle everything", "take care of it", "take care of this", "take care of the", "agent", "go agent", "full agent mode", "work on this until done", "do this step by step", "keep going until done", "operate the computer"), "autonomous", None),
    (("make a plan to", "make a plan for", "plan and do", "plan and execute", "plan to", "tackle the", "take on the project", "plan the project", "work the project", "plan out"), "plan_project", None),
    (("what's the situation", "whats the situation", "what is the situation", "situation report", "sitrep", "give me a sitrep", "status of everything"), "situation", None),
    # ---- ULTRON: advanced research, advice & strategy (advises only) ----
    (("ultron", "ask ultron", "hey ultron", "summon ultron", "bring in ultron"), "ultron_direct", "ultron"),
    (("friday", "ask friday", "hey friday", "summon friday"), "friday_run", "friday"),
    (("tron", "ask tron", "hey tron", "summon tron"), "tron_run", "tron"),
    (("ira", "ask ira", "hey ira", "summon ira"), "ira_run", "ira"),
    (("mythos", "ask mythos", "hey mythos", "summon mythos"), "mythos_run", "mythos"),
    (("how can i improve", "how do i improve", "how to improve", "improve my", "optimize", "optimise", "make this better", "make it better", "improve"), "improve", "ultron"),
    (("what should i do next", "what should i do", "what should i focus on", "what next", "whats next", "what's next", "check in", "check-in", "any suggestions", "what do you suggest", "what do you recommend", "anything i should know"), "check_in", "ultron"),
    (("give me advice", "any advice", "advise me", "your advice", "i need advice", "advice on", "advice", "advise", "how do i", "how can i", "how should i", "how to", "best way to", "whats the best way", "what is the best way", "tips for", "tips on", "recommend", "suggestions for"), "advise", "ultron"),
    (("turn voice on", "voice on", "enable voice"), "voice_on", None),
    (("turn voice off", "voice off", "disable voice"), "voice_off", None),
    (("voice status", "voice check", "voice test", "test voice", "test your voice", "check your voice", "what languages can you speak", "which languages can you speak", "can you speak telugu", "can you speak hindi"), "voice_status", None),
    (("speak in telugu", "speak telugu", "talk in telugu", "respond in telugu", "reply in telugu", "switch to telugu", "speak in hindi", "speak hindi", "talk in hindi", "respond in hindi", "reply in hindi", "switch to hindi", "speak in english", "speak english", "talk in english", "respond in english", "reply in english", "switch to english", "speak in auto", "auto detect language", "detect language", "speak in my language"), "speak_lang", None),
    (("say",), "say_in", None),
    (("show agents", "list agents", "agents"), "show_agents", None),
    (("show permissions", "permissions"), "show_permissions", None),
    (("say hello", "hello", "hi jarvis", "hey jarvis"), "greet", None),
    (("llm status", "llm health", "model status"), "llm_status", None),
    (("use ollama", "use claude", "use perplexity", "use nvidia", "use gemini", "switch to", "use brain", "use model", "switch brain", "auto brain", "smart brain", "automatic brain", "best brain", "pick the best brain", "choose the brain", "route automatically"), "use_model", None),
    (("local brain", "run without claude", "run without cloud", "go fully local", "use only ollama", "no cloud brain", "brain offline", "fully offline brain", "think locally", "local only"), "local_brain", None),
    (("cloud brain", "use the cloud", "re-enable cloud", "allow cloud", "use cloud brain", "back to cloud"), "cloud_brain", None),
    (("status", "system status", "show status"), "status", None),
    (("think", "ask jarvis", "brainstorm"), "ask_llm", None),
]

_PLANS = {
    "daily_briefing": ["Gather open tasks", "Summarize focus", "Surface top 3 priorities"],
    "business_review": ["Read business knowledge", "Assess positioning/pricing/funnel", "List actions"],
    "draft_customer_reply": ["Detect tone", "Draft reply (no auto-send)", "Flag for approval"],
    "ad_hooks": ["Pull brand voice", "Generate hook angles", "Suggest test plan"],
    "improve_product_page": ["Audit page", "Score trust/clarity", "List fixes"],
    "trading_review": ["Summarize watchlist", "Risk checklist", "No trades - research only"],
}

_WAKE = ("hey jarvis", "ok jarvis", "okay jarvis", "yo jarvis", "jarvis please",
         "jarvis can you", "jarvis could you", "jarvis", "hey", "yo", "please",
         "can you please", "can you", "could you", "would you", "i want you to",
         "i need you to", "pls")

_FILLER = {"ask", "agent", "for", "to", "the", "me", "please", "jarvis", "a", "an",
           "my", "now", "folder", "up", "on", "about"}


def _strip_wake(low: str) -> str:
    changed = True
    while changed:
        changed = False
        for w in sorted(_WAKE, key=len, reverse=True):
            if low == w:
                return ""
            if low.startswith(w + " ") or low.startswith(w + ","):
                low = low[len(w):].lstrip(" ,")
                changed = True
                break
    return low


class ReasoningCore:
    def __init__(self, logger=None):
        self.logger = logger

    def classify(self, text: str) -> Intent:
        raw = (text or "").strip()
        low = raw.lower()
        stripped = _strip_wake(low)
        if stripped != low:
            cut = len(raw) - len(stripped)
            raw = raw[cut:].lstrip(" ,") if 0 < cut < len(raw) else raw
            low = stripped
        for phrases, name, agent in _RULES:
            if any(low == p or low.startswith(p + " ") for p in phrases):
                return Intent(name=name, agent=agent, args=self._extract_args(raw, phrases),
                              confidence=0.9, plan=_PLANS.get(name, []))
        return Intent(name="unknown", agent=None, args=raw, confidence=0.2)

    def decompose(self, goal: str) -> list:
        """Heuristic, LLM-free task decomposition. Used as the honest fallback when the
        brain is offline so the orchestrator can still show *how* it would approach a goal
        instead of crashing. Returns an ordered list of plain-language steps."""
        g = (goal or "").strip()
        if not g:
            return ["Clarify the goal with the master."]
        low = g.lower()
        steps = ["Understand the goal: " + g]
        # surface obviously-needed capabilities from keywords, in a sensible order
        if any(k in low for k in ("research", "find out", "look up", "compare", "investigate", "latest", "news")):
            steps.append("Gather information from available sources (web/news/files).")
        if any(k in low for k in ("analy", "assess", "evaluate", "review", "decide", "should i")):
            steps.append("Analyse the findings and weigh the options.")
        if any(k in low for k in ("write", "draft", "create", "build", "make", "generate", "design", "code", "report", "plan")):
            steps.append("Draft the output (held for review before anything is sent or saved externally).")
        if any(k in low for k in ("send", "email", "post", "publish", "buy", "trade", "delete", "install", "deploy")):
            steps.append("Pause for explicit confirmation before any external or irreversible step.")
        steps.append("Verify the result actually happened, then report honestly.")
        return steps

    @staticmethod
    def _extract_args(raw: str, phrases) -> str:
        out = raw.strip()
        plist = sorted(phrases, key=len, reverse=True)
        changed = True
        while changed:
            changed = False
            low = out.lower()
            for p in plist:
                if low == p or low.startswith(p + " "):
                    out = out[len(p):].lstrip(" :,-")
                    changed = True
                    break
        return out
