#!/usr/bin/env python3
"""
Liar's Dice - local network multiplayer server.

Run this on ONE computer that's on the same WiFi/network as everyone playing:

    python liars_dice_server.py

It will print a URL like http://192.168.1.42:8000 -- send that URL to your
coworkers (Slack, email, whatever). Everyone, including you, opens that URL
in a normal web browser. No installs needed on their end, no accounts,
nothing sent over the internet -- it all stays on your local network.

Requires only the Python standard library (Python 3.7+).
"""

import http.server
import socketserver
import json
import re
import socket
import sys
import threading

ROOMS = {}
LOCK = threading.Lock()

INDEX_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
<title>🎲 Liar's Dice</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  :root{
    --bg:#0A0A0A;
    --bg-2:#161514;
    --panel:#1A1816;
    --panel-2:#221F1B;
    --line: rgba(212,175,55,0.28);
    --gold:#D4AF37;
    --gold-bright:#F4D06F;
    --cream:#F2ECDD;
    --muted:#9A9284;
    --danger:#B33A3A;
    --danger-bright:#E2645F;
    --good:#8AA06B;
    --radius-panel: 8px;
    --radius-die: 11px;
    --shadow: 0 10px 30px rgba(0,0,0,0.6);
  }
  *{box-sizing:border-box;}
  html,body{margin:0;padding:0;}
  body{
    min-height:100vh;
    font-family:'IBM Plex Sans', sans-serif;
    color:var(--cream);
    background:
      radial-gradient(1200px 700px at 50% -10%, rgba(212,175,55,0.10) 0%, transparent 60%),
      radial-gradient(1000px 600px at 90% 110%, rgba(212,175,55,0.05) 0%, transparent 55%),
      var(--bg);
    display:flex;
    justify-content:center;
    padding:22px 14px 60px;
  }
  #app{ width:100%; max-width:460px; }
  h1,h2,h3{ font-family:'Fraunces', serif; font-weight:600; margin:0; }
  .brand{
    text-align:center;
    margin-bottom:22px;
  }
  .brand .dice-row{ font-size:30px; letter-spacing:6px; margin-bottom:2px; }
  .brand h1{ font-size:2.1rem; letter-spacing:0.5px; color:var(--gold-bright); }
  .brand p{ margin:6px 0 0; color:var(--muted); font-size:0.92rem; }

  .panel{
    background: linear-gradient(180deg, var(--panel), var(--panel-2));
    border:1px solid var(--line);
    border-radius:var(--radius-panel);
    padding:20px;
    box-shadow: var(--shadow);
    margin-bottom:16px;
  }
  .panel + .panel{ margin-top:0; }
  label{ display:block; font-size:0.8rem; color:var(--muted); margin-bottom:6px; }
  input[type=text]{
    width:100%;
    background:var(--bg-2);
    border:1px solid var(--line);
    border-radius:6px;
    padding:12px 13px;
    color:var(--cream);
    font-family:'IBM Plex Sans', sans-serif;
    font-size:1rem;
    outline:none;
  }
  input[type=text]:focus{ border-color:var(--gold); }
  input[type=text]::placeholder{ color:#6b6355; }
  .field{ margin-bottom:14px; }

  button{
    font-family:'IBM Plex Sans', sans-serif;
    font-weight:600;
    font-size:0.95rem;
    border-radius:6px;
    border:1px solid transparent;
    padding:12px 16px;
    cursor:pointer;
    transition: transform .08s ease, filter .12s ease;
  }
  button:active{ transform: scale(0.98); }
  button:disabled{ opacity:0.4; cursor:not-allowed; }
  .btn-primary{ background:var(--gold); color:#181410; width:100%; }
  .btn-primary:hover:not(:disabled){ filter:brightness(1.08); }
  .btn-secondary{ background:transparent; border:1px solid var(--gold); color:var(--gold-bright); width:100%; }
  .btn-secondary:hover:not(:disabled){ background:rgba(201,162,39,0.1); }
  .btn-danger{ background:var(--danger); color:var(--cream); width:100%; }
  .btn-danger:hover:not(:disabled){ filter:brightness(1.08); }
  .btn-ghost{ background:transparent; border:none; color:var(--muted); font-weight:500; font-size:0.82rem; text-decoration:underline; padding:6px; width:auto; }
  .row{ display:flex; gap:10px; }
  .row > *{ flex:1; }

  .divider{ display:flex; align-items:center; gap:10px; color:var(--muted); font-size:0.78rem; margin:16px 0; }
  .divider::before,.divider::after{ content:''; flex:1; height:1px; background:var(--line); }

  .error{ background:rgba(192,80,63,0.15); border:1px solid var(--danger); color:#F2C9C2; padding:10px 12px; border-radius:6px; font-size:0.85rem; margin-bottom:14px; }

  .code-display{
    text-align:center; letter-spacing:8px; font-family:'Fraunces', serif; font-weight:700;
    font-size:2.1rem; color:var(--gold-bright); padding:14px 0 6px;
  }
  .code-sub{ text-align:center; color:var(--muted); font-size:0.78rem; margin-bottom:10px; }

  .player-list{ list-style:none; margin:0; padding:0; }
  .player-list li{
    display:flex; align-items:center; justify-content:space-between;
    padding:10px 4px; border-bottom:1px solid var(--line); font-size:0.95rem;
  }
  .player-list li:last-child{ border-bottom:none; }
  .table-row{ display:flex; align-items:center; justify-content:space-between; gap:10px; padding:11px 4px; border-bottom:1px solid var(--line); }
  .table-row:last-child{ border-bottom:none; }
  .table-row-title{ font-weight:600; font-size:0.92rem; }
  .table-row-sub{ color:var(--muted); font-size:0.76rem; margin-top:2px; }
  .setting-row{ display:flex; align-items:flex-start; gap:10px; font-size:0.88rem; line-height:1.4; }
  .setting-row input[type=checkbox]{ margin-top:3px; width:17px; height:17px; flex:none; accent-color:var(--gold); }
  .tag{ font-size:0.68rem; color:var(--bg); background:var(--gold); padding:2px 7px; border-radius:20px; font-weight:700; margin-left:8px; }
  .tag-you{ background:var(--cream); }

  .hud{ display:flex; justify-content:space-between; align-items:baseline; margin-bottom:14px; }
  .hud .round{ color:var(--muted); font-size:0.82rem; }
  .hud .code-mini{ color:var(--gold); font-size:0.78rem; letter-spacing:2px; font-weight:600; }

  .turn-banner{
    text-align:center; padding:10px 14px; border-radius:6px; margin-bottom:14px;
    font-size:0.95rem; border:1px solid var(--line);
  }
  .turn-banner.mine{ background:rgba(201,162,39,0.16); border-color:var(--gold); color:var(--gold-bright); font-weight:600; }
  .turn-banner.theirs{ color:var(--muted); }

  .bid-display{ text-align:center; margin-bottom:16px; }
  .bid-display .label{ color:var(--muted); font-size:0.78rem; margin-bottom:6px; }
  .bid-display .value{ font-family:'Fraunces', serif; font-size:1.7rem; color:var(--cream); }
  .bid-display .by{ color:var(--muted); font-size:0.78rem; margin-top:2px; }

  .opponents{ display:flex; flex-wrap:wrap; gap:8px; margin-bottom:16px; }
  .opp-card{
    flex:1 1 calc(50% - 8px); min-width:130px;
    background:var(--bg-2); border:1px solid var(--line); border-radius:6px;
    padding:9px 11px; font-size:0.85rem; display:flex; align-items:center; justify-content:space-between;
  }
  .opp-card.out{ opacity:0.4; }
  .opp-card.active{ border-color:var(--gold); }
  .opp-card .name{ display:flex; align-items:center; gap:6px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;}
  .opp-die-icon{ width:13px; height:13px; background:var(--gold); border-radius:3px; flex:none; }
  .opp-count{ color:var(--muted); font-size:0.8rem; white-space:nowrap; }

  .table-wrap{ position:relative; width:100%; padding-top:82%; margin-bottom:18px; }
  .table-surface{
    position:absolute; left:6%; right:6%; top:8%; bottom:8%; border-radius:50%;
    background: radial-gradient(ellipse at 50% 40%, #221D12 0%, #050403 75%);
    border:6px solid var(--gold); box-shadow: inset 0 0 40px rgba(0,0,0,0.7), inset 0 0 0 2px rgba(212,175,55,0.15), 0 8px 22px rgba(0,0,0,0.6);
  }
  .table-center{
    position:absolute; left:50%; top:50%; transform:translate(-50%,-50%);
    text-align:center; width:62%;
  }
  .table-center .center-label{ color:var(--muted); font-size:0.72rem; letter-spacing:1px; text-transform:uppercase; }
  .table-center .center-bid{ font-family:'Fraunces', serif; color:var(--cream); font-size:1.25rem; margin:2px 0; line-height:1.15; }
  .table-center .center-stake{
    display:inline-block; margin-top:4px; padding:4px 12px; border-radius:20px;
    background:rgba(201,162,39,0.18); border:1px solid var(--gold); color:var(--gold-bright);
    font-weight:700; font-size:0.85rem;
  }
  .table-center .center-stake.hot{ background:rgba(192,80,63,0.22); border-color:var(--danger); color:var(--danger-bright); }
  .table-center .center-zai{ margin-top:6px; font-size:0.68rem; letter-spacing:0.5px; color:var(--danger-bright); font-weight:700; }
  .seat{
    position:absolute; transform:translate(-50%,-50%); width:84px; text-align:center;
  }
  .seat-bubble{
    background:var(--bg-2); border:2px solid var(--line); border-radius:12px;
    padding:6px 4px; font-size:0.72rem; line-height:1.25; color:var(--cream);
    box-shadow:0 3px 8px rgba(0,0,0,0.35);
  }
  .seat.empty .seat-bubble{
    background:transparent; border-style:dashed; color:var(--muted); cursor:pointer;
  }
  .seat.empty .seat-bubble:hover{ border-color:var(--gold); color:var(--gold-bright); }
  .seat.you .seat-bubble{ border-color:var(--gold); }
  .seat.turn .seat-bubble{ border-color:var(--gold); box-shadow:0 0 0 3px rgba(201,162,39,0.35), 0 3px 8px rgba(0,0,0,0.35); }
  .seat .seat-name{ font-weight:600; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .seat .seat-tag{ font-size:0.62rem; color:var(--gold); }
  .seat .seat-drinks{ color:var(--muted); font-size:0.68rem; margin-top:1px; }

  .log{
    max-height:110px; overflow-y:auto; font-size:0.8rem; color:var(--muted);
    background:var(--bg-2); border:1px solid var(--line); border-radius:6px; padding:9px 12px; margin-bottom:16px;
  }
  .log div{ padding:3px 0; }
  .log div:not(:last-child){ border-bottom:1px dashed rgba(255,255,255,0.06); }

  .your-hand{ margin-bottom:16px; }
  .your-hand .label{ color:var(--muted); font-size:0.78rem; margin-bottom:8px; display:flex; justify-content:space-between; }
  .dice-row-real{ display:flex; gap:8px; justify-content:center; }

  .die{
    width:50px; height:50px; background:var(--cream); border-radius:var(--radius-die);
    display:grid; grid-template-columns:repeat(3,1fr); grid-template-rows:repeat(3,1fr);
    padding:8px; box-shadow: 0 3px 0 rgba(0,0,0,0.35), inset 0 0 0 2px rgba(0,0,0,0.05);
    flex:none;
  }
  .die.rolling{ animation: roll 0.5s ease; }
  @keyframes roll{
    0%{ transform: rotate(0deg) scale(1); }
    35%{ transform: rotate(160deg) scale(1.08); }
    70%{ transform: rotate(280deg) scale(0.96); }
    100%{ transform: rotate(360deg) scale(1); }
  }
  .pip{ width:62%; height:62%; margin:auto; border-radius:50%; background:var(--bg); }

  .bid-controls{ }
  .control-block{ margin-bottom:14px; }
  .control-block .label{ color:var(--muted); font-size:0.78rem; margin-bottom:8px; }
  .stepper{ display:flex; align-items:center; justify-content:center; gap:16px; }
  .stepper button{ width:42px; height:42px; padding:0; font-size:1.2rem; background:var(--bg-2); color:var(--cream); border:1px solid var(--line); }
  .stepper .qty{ font-family:'Fraunces', serif; font-size:1.9rem; min-width:44px; text-align:center; }
  .face-picker{ display:flex; gap:7px; justify-content:center; }
  .face-btn{ padding:0; background:var(--bg-2); border:1px solid var(--line); border-radius:8px; width:44px; height:44px; display:grid; grid-template-columns:repeat(3,1fr); grid-template-rows:repeat(3,1fr); padding:6px; }
  .face-btn .pip{ background:var(--muted); }
  .face-btn.selected{ border-color:var(--gold); background:rgba(201,162,39,0.12); }
  .face-btn.selected .pip{ background:var(--gold-bright); }
  .hint{ text-align:center; font-size:0.78rem; color:var(--muted); margin-top:8px; min-height:1em; }
  .hint.bad{ color:var(--danger-bright); }

  .reveal-list{ display:flex; flex-direction:column; gap:8px; margin-bottom:16px; }
  .reveal-row{ display:flex; align-items:center; gap:10px; background:var(--bg-2); border:1px solid var(--line); border-radius:6px; padding:9px 11px; }
  .reveal-row .rname{ width:78px; font-size:0.82rem; flex:none; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .reveal-row .rdice{ display:flex; gap:5px; flex-wrap:wrap; }
  .reveal-row .rdice .die{ width:32px; height:32px; padding:5px; border-radius:7px; box-shadow:none; }
  .waiting-dots{ color: var(--muted); font-size:0.82rem; }

  .result-banner{ text-align:center; padding:16px; border-radius:6px; margin-bottom:16px; border:1px solid var(--line); }
  .result-banner.true{ border-color:var(--good); background:rgba(111,160,107,0.12); }
  .result-banner.false{ border-color:var(--danger); background:rgba(192,80,63,0.12); }
  .result-banner .count-line{ font-family:'Fraunces', serif; font-size:1.3rem; margin-bottom:4px; }
  .result-banner .sub{ color:var(--muted); font-size:0.85rem; }

  .winner-block{ text-align:center; padding:10px 0 4px; }
  .winner-block .trophy{ font-size:2.6rem; }
  .winner-block h2{ font-size:1.5rem; color:var(--gold-bright); margin:6px 0 2px; }
  .winner-block p{ color:var(--muted); margin:0 0 18px; font-size:0.88rem; }

  .footer-link{ text-align:center; margin-top:10px; }
  .rules-body{ font-size:0.87rem; line-height:1.55; color:var(--cream); }
  .rules-body h3{ font-size:0.95rem; margin:14px 0 4px; color:var(--gold-bright); }
  .rules-body p{ margin:0 0 8px; }
  .modal-backdrop{ position:fixed; inset:0; background:rgba(0,0,0,0.55); display:flex; align-items:flex-end; justify-content:center; z-index:50; }
  .modal{ background:var(--panel-2); border:1px solid var(--line); border-radius:14px 14px 0 0; padding:22px 20px 26px; max-width:460px; width:100%; max-height:80vh; overflow-y:auto; }
  .modal h2{ color:var(--gold-bright); margin-bottom:10px; }

  ::-webkit-scrollbar{ width:6px; }
  ::-webkit-scrollbar-thumb{ background:var(--line); border-radius:3px; }
</style>
</head>
<body>
<div id="app"></div>

<script>
(function(){
  "use strict";

  /* ---------------- constants ---------------- */
  var POLL_MS = 1800;
  var NEXT_ROUND_DELAY = 20000;
  var TURN_SECONDS = 60;
  var SEAT_COUNT = 8;

  /* ---------------- session state ---------------- */
  var myId = 'p_' + Math.random().toString(36).slice(2,9);
  var myName = '';
  var roomCode = '';
  var room = null;
  var view = 'landing'; // landing | lobby | game
  var myRole = 'player'; // 'player' | 'spectator'
  var myDice = [];
  var errorMsg = '';
  var showRules = false;
  var pollTimer = null;
  var tickTimer = null;
  var landingPollTimer = null;
  var roomList = [];
  var showJoinByCode = false;

  var draftName = '';
  var draftJoinCode = '';
  var bidQty = 1;
  var bidFace = 2;
  var bidTarget = null; // id of the neighbor chosen to receive the next bid (null = not chosen yet)
  var bidZaiToggle = false; // whether the current bidder is declaring/breaking Zai on this bid

  var flags = { rolledRound: -1, revealRound: -1, scheduledNext: -1, rollingAnim:false, revealAnim:false, timeoutAttempt:null, botAttempted:{} };

  /* ---------------- storage helpers (talks to the local Python server on this same machine) ---------------- */
  function clone(x){ return x ? JSON.parse(JSON.stringify(x)) : x; }

  var lastStorageError = '';

  function storageAvailable(){ return typeof fetch === 'function'; }

  async function getRoomRaw(code){
    try{
      var res = await fetch('/api/room/' + encodeURIComponent(code));
      if (res.status === 404) return null;
      if (!res.ok){ lastStorageError = 'Server error ' + res.status; return null; }
      return await res.json();
    }catch(e){ lastStorageError = String(e && e.message || e); return null; }
  }

  async function getRoomList(){
    try{
      var res = await fetch('/api/rooms');
      if (!res.ok) return [];
      var data = await res.json();
      return data.rooms || [];
    }catch(e){ return []; }
  }

  async function sleep(ms){ return new Promise(function(r){ setTimeout(r, ms); }); }

  // mutator(draft) -> returns new draft object to save, or null/undefined to abort (no write)
  async function mutate(code, mutator){
    for (var i=0; i<8; i++){
      var cur = await getRoomRaw(code);
      if (!cur) return null;
      var draft = clone(cur);
      var next;
      try{ next = mutator(draft); }catch(e){ lastStorageError = String(e && e.message || e); return null; }
      if (next === null || next === undefined) return cur;
      try{
        var res = await fetch('/api/room/' + encodeURIComponent(code) + '/update', {
          method:'POST',
          headers:{'Content-Type':'application/json'},
          body: JSON.stringify({ expectedVersion: cur.version, room: next })
        });
        if (res.status === 409){ await sleep(120 + Math.random()*200); continue; } // someone else updated first, retry
        if (!res.ok){ lastStorageError = 'Server error ' + res.status; await sleep(150); continue; }
        return await res.json();
      }catch(e){
        lastStorageError = String(e && e.message || e);
        await sleep(150 + Math.random()*250);
      }
    }
    return null;
  }

  // Dedicated create path: distinguishes "code collision, try another" from "server actually failed",
  // so the caller can retry codes without accidentally adopting someone else's table.
  async function tryCreateRoom(code, hostId, hostName){
    var newRoom = {
      code: code, phase:'lobby', hostId: hostId,
      players:[{ id: hostId, name: hostName, diceCount:5, alive:true, drinks:0, seat:null }],
      seating:[], currentActor:null, lastFrom:null, currentBid:null, zaiActive:false,
      round:0, rolledPlayers:[], reveal:{}, challenge:null, lastResult:null,
      winner:null, log:['Table created by ' + hostName + '.'],
      settings: { fanPiEnabled: true, unlimitedTime: false },
      spectators: []
    };
    try{
      var res = await fetch('/api/room/' + encodeURIComponent(code) + '/create', {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify(newRoom)
      });
      if (res.status === 409) return { status:'conflict' };
      if (!res.ok){ lastStorageError = 'Server error ' + res.status; return { status:'error' }; }
      return { status:'ok', room: await res.json() };
    }catch(e){
      lastStorageError = String(e && e.message || e);
      return { status:'error' };
    }
  }

  /* ---------------- game helpers ---------------- */
  function nameOf(r, id){
    var p = r.players.find(function(p){ return p.id === id; });
    return p ? p.name : '???';
  }
  function faceLabel(f){ return f === 1 ? 'Ace' : String(f); }
  function describeBid(qty, face){ return qty + ' × ' + (face===1?'Aces':faceLabel(face)+'s'); }
  function faceRank(f){ return f === 1 ? 7 : f; }
  function nextDeadline(draft){
    if (draft.settings && draft.settings.unlimitedTime) return null;
    return Date.now() + TURN_SECONDS*1000;
  }
  function isValidBid(current, next){
    if (next.quantity < 1 || next.face < 1 || next.face > 6) return false;
    if (!current) return true;
    if (next.quantity > current.quantity) return true;
    if (next.quantity === current.quantity && faceRank(next.face) > faceRank(current.face)) return true;
    return false;
  }
  // Minimum legal opening bid (the very first bid of a round) scales with player count:
  // aces need at least N. For any other face, 2-player games only have one higher tier (N+1)
  // whether or not Zai is declared; 3+ player games split it into Zai (N+1) vs normal (N+2).
  function openingMinQty(playerCount, face, zaiDeclared){
    if (face === 1) return playerCount;
    if (playerCount === 2) return playerCount + 1;
    return zaiDeclared ? playerCount + 1 : playerCount + 2;
  }
  // The two people you can pass a bid to, sitting on either side of you in the circle.
  // With exactly 2 players, both "sides" are the same single other player.
  function neighborsOf(seating, playerId){
    var idx = seating.indexOf(playerId);
    var n = seating.length;
    if (idx === -1 || n === 0) return { left:null, right:null };
    return { left: seating[(idx+1)%n], right: seating[(idx-1+n)%n] };
  }
  // Position for seat i of N around an oval table, starting at the top and going clockwise.
  // Returns percentages for absolute positioning within the table container.
  function seatPosition(i, total){
    var angle = -Math.PI/2 + (2*Math.PI*i/total);
    var rx = 44, ry = 40; // radii as % of container
    return {
      left: (50 + rx*Math.cos(angle)).toFixed(1) + '%',
      top: (50 + ry*Math.sin(angle)).toFixed(1) + '%'
    };
  }
  function totalDiceInPlay(r){
    return r.players.filter(function(p){ return p.alive; }).reduce(function(s,p){ return s+p.diceCount; }, 0);
  }

  /* ---------------- bot AI (rough heuristics, not perfect play -- keeps the game moving and mildly sharp) ---------------- */
  function pMatchFor(face, zaiActive){ return (zaiActive || face===1) ? (1/6) : (2/6); }
  function botCountMatches(dice, face, zaiActive){
    return (dice||[]).filter(function(d){ return d===face || (!zaiActive && face!==1 && d===1); }).length;
  }
  function botDecideOpening(r, bot){
    var dice = bot.dice || [];
    var counts = {};
    dice.forEach(function(d){ counts[d] = (counts[d]||0)+1; });
    var bestFace = 2, bestCount = -1;
    for (var f=2; f<=6; f++){ var c = counts[f]||0; if (c > bestCount){ bestCount = c; bestFace = f; } }
    if ((counts[1]||0) >= 2 && Math.random() < 0.3){ bestFace = 1; bestCount = counts[1]; }
    var total = totalDiceInPlay(r);
    var otherDice = total - bot.diceCount;
    var p = pMatchFor(bestFace, false);
    var toggleZai = Math.random() < 0.1;
    var minQty = openingMinQty(r.seating.length, bestFace, toggleZai);
    var qty = Math.max(minQty, Math.min(total, Math.round(bestCount + otherDice*p*0.85)));
    var nb = neighborsOf(r.seating, bot.id);
    var target = Math.random() < 0.5 ? nb.left : nb.right;
    return { qty: qty, face: bestFace, target: target, toggleZai: toggleZai };
  }
  function botDecideContinue(r, bot){
    var cur = r.currentBid;
    var dice = bot.dice || [];
    var wasZaiActive = !!r.zaiActive;
    var selfCount = botCountMatches(dice, cur.face, wasZaiActive);
    var total = totalDiceInPlay(r);
    var otherDice = total - bot.diceCount;
    var p = pMatchFor(cur.face, wasZaiActive);
    var expectedTotal = selfCount + otherDice*p;
    var ratio = cur.quantity > 0 ? expectedTotal / cur.quantity : 2;
    var rnd = Math.random();
    var wantsChallenge = ratio < 0.75 ? (rnd < 0.8) : (ratio <= 1.3 ? (rnd < 0.25) : (rnd < 0.1));

    if (wantsChallenge){
      return { action: (Math.random() < 0.35 ? 'pi' : 'liar') };
    }
    var nb = neighborsOf(r.seating, bot.id);
    // Bots keep it simple and never intentionally reverse.
    var target = (r.lastFrom && nb.left !== r.lastFrom) ? nb.left : (r.lastFrom && nb.right !== r.lastFrom ? nb.right : nb.left);
    var toggleZai = false, qty, face;
    if (wasZaiActive){
      var breakQty = cur.quantity * 2;
      if (Math.random() < 0.15 && breakQty <= total){
        toggleZai = true;
        qty = breakQty;
        face = 1 + Math.floor(Math.random()*6);
      }
    }
    if (!toggleZai){
      qty = cur.quantity + 1;
      face = cur.face;
      if (qty > total){
        qty = cur.quantity;
        face = Math.min(6, cur.face + 1);
        if (faceRank(face) <= faceRank(cur.face)) return { action: 'liar' }; // truly out of legal room -- just challenge
      }
      if (!wasZaiActive && Math.random() < 0.08) toggleZai = true;
    }
    return { qty: qty, face: face, target: target, toggleZai: toggleZai };
  }
  function botDecidePiResponse(r){
    var fanPiAllowed = !r.settings || r.settings.fanPiEnabled !== false;
    if (!fanPiAllowed) return false;
    var bidder = r.players.find(function(p){ return p.id === r.challenge.bidderId; });
    var dice = bidder ? (bidder.dice || []) : [];
    var zaiActive = !!r.challenge.zaiActive;
    var face = r.challenge.bid.face, qty = r.challenge.bid.quantity;
    var selfCount = botCountMatches(dice, face, zaiActive);
    var total = totalDiceInPlay(r);
    var otherDice = bidder ? (total - bidder.diceCount) : total;
    var p = pMatchFor(face, zaiActive);
    var ratio = qty > 0 ? (selfCount + otherDice*p) / qty : 2;
    return ratio > 1.2 && Math.random() < 0.35;
  }

  function rollDice(n){
    var out = [];
    for (var i=0;i<n;i++) out.push(1 + Math.floor(Math.random()*6));
    return out;
  }
  function randomCode(){
    var letters = 'ABCDEFGHJKLMNPQRSTUVWXYZ';
    var s = '';
    for (var i=0;i<4;i++) s += letters[Math.floor(Math.random()*letters.length)];
    return s;
  }

  /* ---------------- mutators ---------------- */
  function mJoin(){
    return mutate(roomCode, function(draft){
      if (!draft) return null;
      if (draft.players.find(function(p){ return p.id===myId; })) return draft;
      if (draft.phase !== 'lobby') return null;
      if (draft.players.length >= SEAT_COUNT) return null;
      draft.players.push({ id: myId, name: myName, diceCount:5, alive:true, drinks:0, seat:null });
      draft.log.push(myName + ' joined the table.');
      // If they were spectating this same table, drop that entry now that they're playing.
      draft.spectators = (draft.spectators || []).filter(function(s){ return s.id !== myId; });
      return draft;
    });
  }

  // Spectators can join at any time, in any phase, and are never part of the seating/turn logic.
  function mSpectate(name){
    return mutate(roomCode, function(draft){
      if (!draft) return null;
      if (draft.players.find(function(p){ return p.id===myId; })) return draft; // already playing, nothing to do
      if (!draft.spectators) draft.spectators = [];
      var existing = draft.spectators.find(function(s){ return s.id===myId; });
      if (existing){ existing.name = name; return draft; }
      draft.spectators.push({ id: myId, name: name });
      return draft;
    });
  }

  function mUpdateSettings(patch){
    return mutate(roomCode, function(draft){
      if (!draft || draft.phase !== 'lobby') return null;
      if (draft.hostId !== myId) return null;
      draft.settings = Object.assign({}, draft.settings, patch);
      return draft;
    });
  }

  function mTakeSeat(seatIndex){
    return mutate(roomCode, function(draft){
      if (!draft || draft.phase !== 'lobby') return null;
      if (seatIndex < 0 || seatIndex >= SEAT_COUNT) return null;
      var me = draft.players.find(function(p){ return p.id===myId; });
      if (!me) return null;
      var taken = draft.players.some(function(p){ return p.id!==myId && p.seat===seatIndex; });
      if (taken) return null;
      me.seat = seatIndex;
      return draft;
    });
  }

  var BOT_NAMES = ['Bot Rex','Bot Nova','Bot Zed','Bot Miko','Bot Otto','Bot Ivy','Bot Ace','Bot Luna'];

  function mAddBot(){
    return mutate(roomCode, function(draft){
      if (!draft || draft.phase !== 'lobby') return null;
      if (draft.hostId !== myId) return null;
      var usedSeats = draft.players.map(function(p){ return p.seat; }).filter(function(s){ return s!==null && s!==undefined; });
      var openSeat = -1;
      for (var i=0;i<SEAT_COUNT;i++){ if (usedSeats.indexOf(i)===-1){ openSeat=i; break; } }
      if (openSeat === -1) return null; // table full
      var usedNames = draft.players.map(function(p){ return p.name; });
      var name = BOT_NAMES.find(function(n){ return usedNames.indexOf(n)===-1; }) || ('Bot ' + Math.random().toString(36).slice(2,5));
      draft.players.push({ id: 'bot_' + Math.random().toString(36).slice(2,9), name: name, diceCount:5, alive:true, drinks:0, seat:openSeat, isBot:true });
      draft.log.push(name + ' (bot) joined the table.');
      return draft;
    });
  }

  function mRemoveBot(botId){
    return mutate(roomCode, function(draft){
      if (!draft || draft.phase !== 'lobby') return null;
      if (draft.hostId !== myId) return null;
      var idx = draft.players.findIndex(function(p){ return p.id===botId && p.isBot; });
      if (idx === -1) return null;
      var name = draft.players[idx].name;
      draft.players.splice(idx, 1);
      draft.log.push(name + ' (bot) was removed.');
      return draft;
    });
  }

  function mStart(){
    return mutate(roomCode, function(draft){
      if (!draft || draft.phase !== 'lobby' || draft.players.length < 2) return null;
      if (!draft.players.every(function(p){ return p.seat !== null && p.seat !== undefined; })) return null;
      var seating = draft.players.slice().sort(function(a,b){ return a.seat - b.seat; }).map(function(p){ return p.id; });
      draft.players.forEach(function(p){ p.diceCount=5; p.alive=true; p.drinks=0; p.dice=null; });
      draft.seating = seating;
      draft.currentActor = seating[0];
      draft.lastFrom = null;
      draft.currentBid = null;
      draft.zaiActive = false;
      draft.round = 1;
      draft.rolledPlayers = [];
      draft.reveal = {};
      draft.challenge = null;
      draft.lastResult = null;
      draft.winner = null;
      draft.phase = 'rolling';
      draft.log = ['Round 1 — everyone rolls!'];
      return draft;
    });
  }

  function mMarkRolled(){
    return mutate(roomCode, function(draft){
      if (!draft || draft.phase !== 'rolling') return null;
      var me = draft.players.find(function(p){ return p.id===myId; });
      if (!me || !me.alive) return null;
      if (draft.rolledPlayers.indexOf(myId) !== -1) return draft;
      draft.rolledPlayers.push(myId);
      var aliveCount = draft.players.filter(function(p){ return p.alive; }).length;
      if (draft.rolledPlayers.length >= aliveCount){
        draft.phase = 'bidding';
        draft.turnDeadline = nextDeadline(draft);
        draft.log.push('All dice rolled. ' + nameOf(draft, draft.currentActor) + ' opens the bidding.');
      }
      return draft;
    });
  }

  // A bot has no browser of its own, so any connected human's client rolls on its behalf
  // and stores the result in shared state (bots have no privacy to protect).
  function mBotRoll(botId){
    return mutate(roomCode, function(draft){
      if (!draft || draft.phase !== 'rolling') return null;
      var bot = draft.players.find(function(p){ return p.id===botId && p.isBot; });
      if (!bot || !bot.alive) return null;
      if (draft.rolledPlayers.indexOf(botId) !== -1) return draft;
      bot.dice = rollDice(bot.diceCount);
      draft.rolledPlayers.push(botId);
      var aliveCount = draft.players.filter(function(p){ return p.alive; }).length;
      if (draft.rolledPlayers.length >= aliveCount){
        draft.phase = 'bidding';
        draft.turnDeadline = nextDeadline(draft);
        draft.log.push('All dice rolled. ' + nameOf(draft, draft.currentActor) + ' opens the bidding.');
      }
      return draft;
    });
  }

  function mPlaceBid(qty, face, targetId, toggleZai, actingIdOverride){
    var actorId = actingIdOverride || myId;
    return mutate(roomCode, function(draft){
      if (!draft || draft.phase !== 'bidding') return null;
      if (draft.currentActor !== actorId) return null;
      var n = draft.seating.length;
      var nb = neighborsOf(draft.seating, actorId);
      // With exactly 2 players there's only one possible recipient -- no choice needed, no reverse penalty.
      if (n === 2){
        targetId = nb.left;
      } else {
        if (targetId !== nb.left && targetId !== nb.right) return null;
      }
      var isReverse = n > 2 && draft.lastFrom !== null && targetId === draft.lastFrom;
      var wasZaiActive = !!draft.zaiActive;
      var breakingZai = wasZaiActive && !!toggleZai;

      if (face < 1 || face > 6) return null;
      if (draft.currentBid){
        if (breakingZai){
          var minQty = draft.currentBid.quantity * 2 + (isReverse ? 2 : 0);
          if (qty < minQty) return null;
        } else if (isReverse){
          if (qty < draft.currentBid.quantity + 2) return null;
        } else {
          if (!isValidBid(draft.currentBid, { quantity: qty, face: face })) return null;
        }
      } else {
        var openMin = openingMinQty(n, face, !!toggleZai);
        if (qty < openMin) return null;
      }

      var newZaiActive = wasZaiActive !== !!toggleZai; // XOR: off->on (declare, free) or on->off (break, costly)
      draft.currentBid = { quantity: qty, face: face, by: actorId };
      draft.zaiActive = newZaiActive;
      draft.lastFrom = actorId;
      draft.currentActor = targetId;
      draft.turnDeadline = nextDeadline(draft);
      var tag = '';
      if (breakingZai) tag = ' \u2014 BREAKING ZAI!';
      else if (!wasZaiActive && toggleZai) tag = ' \u2014 calling ZAI (1s don\u2019t count)';
      draft.log.push(nameOf(draft, actorId) + ' bids ' + describeBid(qty, face) + tag + (isReverse ? ' \u2014 REVERSING back to ' : ' \u2014 passing to ') + nameOf(draft, targetId) + '.');
      return draft;
    });
  }

  // Seeds reveal entries for any bot still alive (bots have no browser to submit their own),
  // then resolves the challenge immediately if everyone alive now has a reveal entry.
  function finishRevealIfReady(draft){
    draft.players.forEach(function(p){
      if (p.isBot && p.alive && !draft.reveal[p.id] && p.dice){
        draft.reveal[p.id] = p.dice.slice();
      }
    });
    var aliveIds = draft.players.filter(function(p){ return p.alive; }).map(function(p){ return p.id; });
    var allIn = aliveIds.every(function(id){ return !!draft.reveal[id]; });
    if (!allIn) return;
    var face = draft.challenge.bid.face, qty = draft.challenge.bid.quantity;
    var multiplier = draft.challenge.multiplier || 1;
    var zaiWasActive = !!draft.challenge.zaiActive;
    var count = 0;
    aliveIds.forEach(function(id){
      draft.reveal[id].forEach(function(d){
        if (d === face || (!zaiWasActive && face !== 1 && d === 1)) count++;
      });
    });
    var bidTrue = count >= qty;
    var loserId = bidTrue ? draft.challenge.challengerId : draft.challenge.bidderId;
    var loser = draft.players.find(function(p){ return p.id===loserId; });
    loser.drinks = (loser.drinks || 0) + multiplier;
    draft.lastResult = { count:count, quantity:qty, face:face, bidTrue:bidTrue, loserId:loserId, loserName:loser.name, multiplier:multiplier, zaiActive:zaiWasActive };
    draft.log.push('Count of ' + faceLabel(face) + 's (' + (zaiWasActive ? 'Zai \u2014 1s don\u2019t count' : 'wild Aces included') + ') = ' + count + ' vs bid ' + qty + '. ' + (bidTrue ? 'Bid holds \u2014 ' : 'Bluff caught \u2014 ') + loser.name + ' drinks ' + multiplier + (multiplier===1?'':'\u00d7') + '!');
    draft.phase = 'roundend';
  }

  function mChallenge(kind, actingIdOverride){
    // kind: 'liar' (1x, resolves immediately) or 'pi' (2x, gives the bidder a chance to respond)
    var actorId = actingIdOverride || myId;
    return mutate(roomCode, function(draft){
      if (!draft || draft.phase !== 'bidding' || !draft.currentBid) return null;
      if (draft.currentActor !== actorId) return null;
      var bidderId = draft.currentBid.by;
      var bidSnapshot = { quantity: draft.currentBid.quantity, face: draft.currentBid.face };
      var zaiSnapshot = !!draft.zaiActive;
      if (kind === 'pi'){
        draft.challenge = { challengerId: actorId, bidderId: bidderId, bid: bidSnapshot, multiplier: 2, zaiActive: zaiSnapshot };
        draft.phase = 'pi_response';
        draft.turnDeadline = nextDeadline(draft);
        draft.log.push(nameOf(draft, actorId) + ' calls PI on ' + nameOf(draft, bidderId) + '\u2019s bid of ' + describeBid(bidSnapshot.quantity, bidSnapshot.face) + '! (2\u00d7 drinks on the line)');
      } else {
        draft.challenge = { challengerId: actorId, bidderId: bidderId, bid: bidSnapshot, multiplier: 1, zaiActive: zaiSnapshot };
        draft.reveal = {};
        draft.phase = 'reveal';
        draft.turnDeadline = null;
        draft.log.push(nameOf(draft, actorId) + ' calls Liar on ' + nameOf(draft, bidderId) + '\u2019s bid of ' + describeBid(bidSnapshot.quantity, bidSnapshot.face) + '!');
        finishRevealIfReady(draft);
      }
      return draft;
    });
  }

  // Called by the bidder being PI'd -- escalate === true means Fan Pi (4x, final), false means accept the 2x.
  function mRespondPi(escalate, actingIdOverride){
    var actorId = actingIdOverride || myId;
    return mutate(roomCode, function(draft){
      if (!draft || draft.phase !== 'pi_response' || !draft.challenge) return null;
      if (draft.challenge.bidderId !== actorId) return null;
      var fanPiAllowed = !draft.settings || draft.settings.fanPiEnabled !== false;
      if (escalate && !fanPiAllowed) return null;
      if (escalate){
        draft.challenge.multiplier = 4;
        draft.log.push(nameOf(draft, actorId) + ' fires back FAN PI! Stakes are now 4\u00d7.');
      } else {
        draft.log.push(nameOf(draft, actorId) + ' accepts the PI. Stakes stay at 2\u00d7.');
      }
      draft.reveal = {};
      draft.phase = 'reveal';
      draft.turnDeadline = null;
      finishRevealIfReady(draft);
      return draft;
    });
  }

  // Any client can trigger this once a deadline has passed -- it acts on behalf of
  // whoever's turn it is, not the caller, so it works regardless of who notices first.
  function mForceTimeout(){
    return mutate(roomCode, function(draft){
      if (!draft || !draft.turnDeadline || Date.now() < draft.turnDeadline) return null;

      if (draft.phase === 'pi_response' && draft.challenge){
        // Bidder didn't respond in time -- default to accepting the Pi rather than escalating for them.
        draft.log.push('\u23f1\ufe0f ' + nameOf(draft, draft.challenge.bidderId) + ' ran out of time and auto-accepted the PI. Stakes stay at 2\u00d7.');
        draft.reveal = {};
        draft.phase = 'reveal';
        draft.turnDeadline = null;
        finishRevealIfReady(draft);
        return draft;
      }

      if (draft.phase !== 'bidding') return null;
      var actingId = draft.currentActor;
      if (draft.currentBid){
        var bidderId = draft.currentBid.by;
        draft.challenge = { challengerId: actingId, bidderId: bidderId, bid: { quantity: draft.currentBid.quantity, face: draft.currentBid.face }, multiplier: 1, zaiActive: !!draft.zaiActive };
        draft.reveal = {};
        draft.phase = 'reveal';
        draft.turnDeadline = null;
        draft.log.push('\u23f1\ufe0f ' + nameOf(draft, actingId) + ' ran out of time and auto-called Liar on ' + nameOf(draft, bidderId) + '\u2019s bid of ' + describeBid(draft.currentBid.quantity, draft.currentBid.face) + '.');
        finishRevealIfReady(draft);
      } else {
        var face = 2;
        var qty = openingMinQty(draft.seating.length, face, false);
        var nb = neighborsOf(draft.seating, actingId);
        var target = nb.left;
        draft.currentBid = { quantity: qty, face: face, by: actingId };
        draft.lastFrom = actingId;
        draft.currentActor = target;
        draft.turnDeadline = nextDeadline(draft);
        draft.log.push('\u23f1\ufe0f ' + nameOf(draft, actingId) + ' ran out of time \u2014 auto-bid ' + describeBid(qty, face) + ' to ' + nameOf(draft, target) + '.');
      }
      return draft;
    });
  }

  function mSubmitReveal(dice, actingIdOverride){
    var actorId = actingIdOverride || myId;
    return mutate(roomCode, function(draft){
      if (!draft || draft.phase !== 'reveal') return null;
      var me = draft.players.find(function(p){ return p.id===actorId; });
      if (!me || !me.alive) return null;
      if (draft.reveal[actorId]) return draft;
      draft.reveal[actorId] = dice.slice();
      finishRevealIfReady(draft);
      return draft;
    });
  }

  function mNextRound(){
    return mutate(roomCode, function(draft){
      if (!draft || draft.phase !== 'roundend') return null;
      var loserId = draft.lastResult.loserId;
      draft.currentActor = loserId;
      draft.lastFrom = null;
      draft.currentBid = null;
      draft.zaiActive = false;
      draft.rolledPlayers = [];
      draft.reveal = {};
      draft.challenge = null;
      draft.round += 1;
      draft.phase = 'rolling';
      draft.log.push('Round ' + draft.round + ' \u2014 ' + nameOf(draft, loserId) + ' starts the bidding.');
      return draft;
    });
  }

  function mPlayAgain(){
    return mutate(roomCode, function(draft){
      if (!draft || draft.phase !== 'gameover') return null;
      resetToLobbyDraft(draft);
      draft.log.push('New round set up. Waiting for host to start.');
      return draft;
    });
  }

  function mResetTable(){
    return mutate(roomCode, function(draft){
      if (!draft) return null;
      if (draft.hostId !== myId) return null;
      resetToLobbyDraft(draft);
      draft.log.push('Host ended the game. Table reset.');
      return draft;
    });
  }

  function resetToLobbyDraft(draft){
    draft.phase = 'lobby';
    draft.players.forEach(function(p){ p.diceCount=5; p.alive=true; p.drinks=0; });
    draft.seating = []; draft.currentActor = null; draft.lastFrom = null;
    draft.currentBid = null; draft.zaiActive = false; draft.round = 0; draft.rolledPlayers = [];
    draft.reveal = {}; draft.challenge = null; draft.lastResult = null; draft.winner = null;
  }

  /* ---------------- side-effect reactions on new room state ---------------- */
  function reactToRoom(r){
    if (!r) return;
    var me = r.players.find(function(p){ return p.id===myId; });
    if (r.phase === 'rolling' && me && me.alive && r.rolledPlayers.indexOf(myId) === -1 && flags.rolledRound !== r.round){
      flags.rolledRound = r.round;
      myDice = rollDice(me.diceCount);
      flags.rollingAnim = true;
      mMarkRolled();
    }
    if (r.phase === 'reveal' && me && me.alive && !r.reveal[myId] && flags.revealRound !== r.round){
      flags.revealRound = r.round;
      mSubmitReveal(myDice);
    }
    if (r.phase === 'roundend' && flags.scheduledNext !== r.round){
      flags.scheduledNext = r.round;
      setTimeout(function(){ mNextRound(); }, NEXT_ROUND_DELAY);
    }
    if (r.phase === 'bidding'){
      var cur = r.currentBid;
      var total = totalDiceInPlay(r);
      if (cur){
        if (bidQty <= cur.quantity && bidFace <= cur.face) { bidQty = cur.quantity + 1; bidFace = 2; }
      } else {
        var openMin = openingMinQty(r.seating.length, bidFace, bidZaiToggle);
        if (bidQty < openMin) bidQty = openMin;
      }
      if (bidQty < 1) bidQty = 1;
      if (bidQty > total) bidQty = total;

      if (r.currentActor === myId){
        var nb = neighborsOf(r.seating, myId);
        var validTargets = [nb.left, nb.right];
        if (validTargets.indexOf(bidTarget) === -1){
          // Default to the "continue" neighbor (not whoever just sent it to us) when possible.
          bidTarget = (r.lastFrom && nb.left !== r.lastFrom) ? nb.left : (r.lastFrom && nb.right !== r.lastFrom ? nb.right : nb.left);
        }
      } else {
        bidTarget = null;
      }
    }
    if ((r.phase === 'bidding' || r.phase === 'pi_response') && r.turnDeadline && Date.now() >= r.turnDeadline){
      var timeoutKey = r.phase + ':' + r.round + ':' + r.currentActor + ':' + r.turnDeadline;
      if (flags.timeoutAttempt !== timeoutKey){
        flags.timeoutAttempt = timeoutKey;
        mForceTimeout();
      }
    }
    maybeActForBots(r);
  }

  // Bots have no browser of their own -- whichever human's tab notices it's a bot's turn
  // schedules a short "thinking" delay and then acts on the bot's behalf. Safe to run from
  // multiple tabs at once: the mutators re-check identity/state on every retry, so only the
  // first successful write sticks and the rest quietly no-op.
  function maybeActForBots(r){
    if (r.phase === 'rolling'){
      r.players.forEach(function(p){
        if (p.isBot && p.alive && r.rolledPlayers.indexOf(p.id) === -1){
          var key = 'roll:' + r.round + ':' + p.id;
          if (!flags.botAttempted[key]){
            flags.botAttempted[key] = true;
            setTimeout(function(){ executeBotRoll(p.id); }, 250 + Math.random()*500);
          }
        }
      });
    }
    if (r.phase === 'bidding' && r.currentActor){
      var actor = r.players.find(function(p){ return p.id === r.currentActor; });
      if (actor && actor.isBot){
        var bidSig = r.currentBid ? (r.currentBid.quantity + '-' + r.currentBid.face) : 'open';
        var key2 = 'bid:' + r.round + ':' + r.currentActor + ':' + bidSig + ':' + r.lastFrom;
        if (!flags.botAttempted[key2]){
          flags.botAttempted[key2] = true;
          setTimeout(function(){ executeBotBidTurn(actor.id); }, 900 + Math.random()*1800);
        }
      }
    }
    if (r.phase === 'pi_response' && r.challenge){
      var bidder = r.players.find(function(p){ return p.id === r.challenge.bidderId; });
      if (bidder && bidder.isBot){
        var key3 = 'pi:' + r.round + ':' + r.challenge.bidderId + ':' + r.turnDeadline;
        if (!flags.botAttempted[key3]){
          flags.botAttempted[key3] = true;
          setTimeout(function(){ executeBotPiResponse(bidder.id); }, 900 + Math.random()*1500);
        }
      }
    }
  }

  async function executeBotRoll(botId){
    var fresh = await getRoomRaw(roomCode);
    if (!fresh || fresh.phase !== 'rolling' || fresh.rolledPlayers.indexOf(botId) !== -1) return;
    await mBotRoll(botId);
    var updated = await getRoomRaw(roomCode);
    if (updated){ room = updated; reactToRoom(updated); render(); }
  }

  async function executeBotBidTurn(botId){
    var fresh = await getRoomRaw(roomCode);
    if (!fresh || fresh.phase !== 'bidding' || fresh.currentActor !== botId) return;
    var bot = fresh.players.find(function(p){ return p.id === botId; });
    if (!bot) return;
    if (!fresh.currentBid){
      var opening = botDecideOpening(fresh, bot);
      await mPlaceBid(opening.qty, opening.face, opening.target, opening.toggleZai, botId);
    } else {
      var decision = botDecideContinue(fresh, bot);
      if (decision.action === 'liar' || decision.action === 'pi'){
        await mChallenge(decision.action, botId);
      } else {
        await mPlaceBid(decision.qty, decision.face, decision.target, decision.toggleZai, botId);
      }
    }
    var updated = await getRoomRaw(roomCode);
    if (updated){ room = updated; reactToRoom(updated); render(); }
  }

  async function executeBotPiResponse(botId){
    var fresh = await getRoomRaw(roomCode);
    if (!fresh || fresh.phase !== 'pi_response' || !fresh.challenge || fresh.challenge.bidderId !== botId) return;
    var escalate = botDecidePiResponse(fresh);
    await mRespondPi(escalate, botId);
    var updated = await getRoomRaw(roomCode);
    if (updated){ room = updated; reactToRoom(updated); render(); }
  }

  /* ---------------- polling ---------------- */
  function startPolling(){
    stopPolling();
    pollTimer = setInterval(async function(){
      if (!roomCode) return;
      var r = await getRoomRaw(roomCode);
      if (r){
        room = r;
        reactToRoom(r);
        render();
      }
    }, POLL_MS);
    // Lightweight local tick so the countdown visibly counts down between polls
    // (no network call -- just redraws using the deadline already in `room`).
    tickTimer = setInterval(function(){
      if (room && (room.phase === 'bidding' || room.phase === 'pi_response') && room.turnDeadline) render();
    }, 1000);
  }
  function stopPolling(){
    if (pollTimer) clearInterval(pollTimer); pollTimer = null;
    if (tickTimer) clearInterval(tickTimer); tickTimer = null;
  }

  function startLandingPoll(){
    stopLandingPoll();
    async function tick(){
      roomList = await getRoomList();
      if (view === 'landing') render();
    }
    tick();
    landingPollTimer = setInterval(tick, 2500);
  }
  function stopLandingPoll(){
    if (landingPollTimer) clearInterval(landingPollTimer); landingPollTimer = null;
  }

  /* ---------------- pip map ---------------- */
  var PIPS = {
    1:[[2,2]],
    2:[[1,1],[3,3]],
    3:[[1,1],[2,2],[3,3]],
    4:[[1,1],[1,3],[3,1],[3,3]],
    5:[[1,1],[1,3],[2,2],[3,1],[3,3]],
    6:[[1,1],[1,3],[2,1],[2,3],[3,1],[3,3]]
  };
  function dieHTML(value, extraClass){
    var pips = PIPS[value] || [];
    var inner = pips.map(function(rc){
      return '<span class="pip" style="grid-row:' + rc[0] + ';grid-column:' + rc[1] + ';"></span>';
    }).join('');
    return '<div class="die ' + (extraClass||'') + '">' + inner + '</div>';
  }
  function faceBtnHTML(value){
    var pips = PIPS[value] || [];
    var inner = pips.map(function(rc){
      return '<span class="pip" style="grid-row:' + rc[0] + ';grid-column:' + rc[1] + ';"></span>';
    }).join('');
    var sel = bidFace === value ? ' selected' : '';
    return '<button class="face-btn' + sel + '" data-action="pick-face" data-face="' + value + '">' + inner + '</button>';
  }

  function esc(s){
    return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  /* ---------------- render ---------------- */
  function render(){
    var app = document.getElementById('app');
    var html = '';
    html += brandHTML();
    if (errorMsg) html += '<div class="error">' + esc(errorMsg) + '</div>';

    if (view === 'landing') html += landingHTML();
    else if (room && room.phase === 'lobby') html += lobbyHTML(room);
    else if (room) html += gameHTML(room);
    else html += '<div class="panel">Loading table\u2026</div>';

    if (view !== 'landing'){
      var amHost = room && room.hostId === myId;
      html += '<div class="footer-link"><button class="btn-ghost" data-action="show-rules">How to play</button>' +
        (amHost ? ' &nbsp;\u00b7&nbsp; <button class="btn-ghost" data-action="reset-table">End game</button>' : '') +
        ' &nbsp;\u00b7&nbsp; <button class="btn-ghost" data-action="leave">Leave</button></div>';
    } else {
      html += '<div class="footer-link"><button class="btn-ghost" data-action="show-rules">How to play</button></div>';
    }

    app.innerHTML = html;
    if (showRules) app.innerHTML += rulesModalHTML();
  }

  function brandHTML(){
    return '' +
      '<div class="brand">' +
        '<div class="dice-row">\uD83C\uDFB2</div>' +
        '<h1>Liar\u2019s Dice</h1>' +
        '<p>' + (view==='landing' ? 'An office table for bluffing and calling bluffs.' : (room ? 'Table ' + room.code : '')) + '</p>' +
      '</div>';
  }

  function landingHTML(){
    var listHtml = '';
    if (roomList.length === 0){
      listHtml = '<div style="text-align:center;color:var(--muted);font-size:0.85rem;padding:10px 0;">No tables yet on this network \u2014 be the first to create one.</div>';
    } else {
      listHtml = roomList.map(function(t){
        var statusLabel = t.phase === 'lobby' ? 'Waiting for players' : ('In progress \u2014 round ' + t.round);
        var actionLabel = t.phase === 'lobby' ? 'Join' : 'Watch';
        var action = t.phase === 'lobby' ? 'browse-join' : 'browse-spectate';
        return '<div class="table-row">' +
          '<div class="table-row-info">' +
            '<div class="table-row-title">' + esc(t.hostName) + '\u2019s table</div>' +
            '<div class="table-row-sub">' + statusLabel + ' \u2022 ' + t.playerCount + ' player' + (t.playerCount===1?'':'s') + (t.spectatorCount ? ' \u2022 ' + t.spectatorCount + ' watching' : '') + '</div>' +
          '</div>' +
          '<button class="btn-secondary" data-action="' + action + '" data-code="' + esc(t.code) + '">' + actionLabel + '</button>' +
        '</div>';
      }).join('');
    }
    return '' +
      '<div class="panel">' +
        '<div class="field">' +
          '<label>Your name</label>' +
          '<input type="text" id="nameInput" placeholder="e.g. Priya" value="' + esc(draftName) + '" maxlength="20">' +
        '</div>' +
        '<button class="btn-primary" data-action="create">Create a new table</button>' +
      '</div>' +
      '<div class="panel">' +
        '<div class="label" style="margin-bottom:10px;">Tables on this network</div>' +
        listHtml +
      '</div>' +
      (showJoinByCode ?
        ('<div class="panel">' +
          '<div class="field">' +
            '<label>Table code</label>' +
            '<input type="text" id="codeInput" placeholder="e.g. WXYZ" value="' + esc(draftJoinCode) + '" maxlength="4" style="text-transform:uppercase;letter-spacing:4px;text-align:center;">' +
          '</div>' +
          '<button class="btn-secondary" data-action="join">Join by code</button>' +
        '</div>') :
        '<div class="footer-link"><button class="btn-ghost" data-action="show-join-code">Have a table code instead?</button></div>'
      );
  }

  function lobbyTableHTML(r){
    var isHost = r.hostId === myId;
    var bySeat = {};
    r.players.forEach(function(p){ if (p.seat !== null && p.seat !== undefined) bySeat[p.seat] = p; });
    var seatsHtml = '';
    for (var i=0;i<SEAT_COUNT;i++){
      var pos = seatPosition(i, SEAT_COUNT);
      var occ = bySeat[i];
      var style = 'left:' + pos.left + ';top:' + pos.top + ';';
      if (occ){
        var cls = 'seat' + (occ.id===myId ? ' you' : '');
        seatsHtml += '<div class="' + cls + '" style="' + style + '">' +
          '<div class="seat-bubble">' +
            '<div class="seat-name">' + esc(occ.name) + (occ.isBot ? ' \uD83E\uDD16' : '') + '</div>' +
            (occ.id===r.hostId ? '<div class="seat-tag">HOST</div>' : '') +
            (occ.id===myId ? '<div class="seat-tag">YOU</div>' : '') +
            (occ.isBot && isHost ? '<button class="btn-ghost" style="padding:2px;font-size:0.62rem;" data-action="remove-bot" data-id="' + esc(occ.id) + '">remove</button>' : '') +
          '</div>' +
        '</div>';
      } else {
        seatsHtml += '<div class="seat empty" style="' + style + '" data-action="take-seat" data-seat="' + i + '">' +
          '<div class="seat-bubble">Tap to<br>sit here</div>' +
        '</div>';
      }
    }
    var unseated = r.players.filter(function(p){ return p.seat===null || p.seat===undefined; });
    return '<div class="table-wrap">' +
        '<div class="table-surface"></div>' +
        '<div class="table-center"><div class="center-label">Table</div><div class="center-bid">' + esc(r.code) + '</div></div>' +
        seatsHtml +
      '</div>' +
      (unseated.length ? '<div class="hint" style="margin-bottom:14px;">Still picking a seat: ' + unseated.map(function(p){ return esc(p.name); }).join(', ') + '</div>' : '');
  }

  function lobbyHTML(r){
    var isHost = r.hostId === myId;
    var isPlayerHere = r.players.some(function(p){ return p.id === myId; });
    var allSeated = r.players.every(function(p){ return p.seat !== null && p.seat !== undefined; });
    var canStart = r.players.length >= 2 && allSeated;
    var startLabel = r.players.length < 2 ? 'Need at least 2 players' : (!allSeated ? 'Everyone needs to pick a seat' : 'Start game');
    var settings = r.settings || { fanPiEnabled: true };
    var fanPiOn = settings.fanPiEnabled !== false;
    var unlimitedTimeOn = !!settings.unlimitedTime;
    var tableFull = r.players.length >= SEAT_COUNT;
    var spectators = r.spectators || [];
    return '' +
      (!isPlayerHere ? '<div class="turn-banner theirs">\uD83D\uDC40 You\u2019re spectating \u2014 you\u2019ll see everything once the game starts</div>' : '') +
      '<div class="panel">' +
        '<div class="code-display">' + esc(r.code) + '</div>' +
        '<div class="code-sub">Share this code \u2014 everyone opens this same page and picks a seat.</div>' +
        lobbyTableHTML(r) +
        (isHost ? ('<button class="btn-secondary" data-action="add-bot"' + (tableFull?' disabled':'') + '>' + (tableFull ? 'Table full' : '+ Add a bot player') + '</button>') : '') +
        (spectators.length ? ('<div class="hint" style="margin-top:10px;">Watching: ' + spectators.map(function(s){ return esc(s.name); }).join(', ') + '</div>') : '') +
      '</div>' +
      '<div class="panel">' +
        '<div class="label" style="margin-bottom:10px;">Game rules</div>' +
        '<label class="setting-row" style="' + (isHost?'cursor:pointer;':'opacity:0.7;') + 'margin-bottom:10px;">' +
          '<input type="checkbox" ' + (fanPiOn?'checked':'') + (isHost?' data-action="toggle-fanpi"':' disabled') + '>' +
          '<span><strong>Fan Pi</strong> \u2014 let the bidder escalate a PI to 4\u00d7 instead of just accepting 2\u00d7' + (isHost?'':' (host only)') + '</span>' +
        '</label>' +
        '<label class="setting-row" style="' + (isHost?'cursor:pointer;':'opacity:0.7;') + '">' +
          '<input type="checkbox" ' + (unlimitedTimeOn?'checked':'') + (isHost?' data-action="toggle-unlimited-time"':' disabled') + '>' +
          '<span><strong>Unlimited thinking time</strong> \u2014 turn off the 60-second timer entirely' + (isHost?'':' (host only)') + '</span>' +
        '</label>' +
      '</div>' +
      '<div class="panel">' +
        (isHost ?
          ('<button class="btn-primary" data-action="start"' + (canStart?'':' disabled') + '>' + startLabel + '</button>') :
          ('<div style="text-align:center;color:var(--muted);font-size:0.9rem;">Waiting for the host to start the game\u2026</div>')
        ) +
      '</div>';
  }

  function currentStakeMultiplier(r){
    if (r.phase === 'pi_response' && r.challenge) return r.challenge.multiplier || 2;
    if (r.phase === 'reveal' && r.challenge) return r.challenge.multiplier || 1;
    if (r.phase === 'roundend' && r.lastResult) return r.lastResult.multiplier || 1;
    return 1;
  }

  function gameTableHTML(r){
    var ids = (r.seating && r.seating.length) ? r.seating : r.players.map(function(p){ return p.id; });
    var n = ids.length;
    var seatsHtml = '';
    ids.forEach(function(id, i){
      var occ = r.players.find(function(p){ return p.id === id; });
      if (!occ) return;
      var pos = seatPosition(i, n);
      var isTurn = (r.currentActor === occ.id) && (r.phase === 'bidding' || r.phase === 'pi_response');
      var cls = 'seat' + (occ.id===myId ? ' you' : '') + (isTurn ? ' turn' : '');
      seatsHtml += '<div class="' + cls + '" style="left:' + pos.left + ';top:' + pos.top + ';">' +
        '<div class="seat-bubble">' +
          '<div class="seat-name">' + esc(occ.name) + (occ.isBot ? ' \uD83E\uDD16' : '') + (occ.id===myId ? ' (you)' : '') + '</div>' +
          '<div class="seat-drinks">\uD83C\uDF7A\u00d7' + (occ.drinks||0) + '</div>' +
        '</div>' +
      '</div>';
    });
    var mult = currentStakeMultiplier(r);
    var stakeClass = 'center-stake' + (mult >= 4 ? ' hot' : '');
    var centerBidText = r.currentBid ? describeBid(r.currentBid.quantity, r.currentBid.face) : (r.phase==='rolling' ? 'Rolling\u2026' : 'No bid yet');
    var zaiForDisplay;
    if (r.phase === 'pi_response' || r.phase === 'reveal'){ zaiForDisplay = r.challenge ? !!r.challenge.zaiActive : false; }
    else if (r.phase === 'roundend'){ zaiForDisplay = r.lastResult ? !!r.lastResult.zaiActive : false; }
    else { zaiForDisplay = !!r.zaiActive; }
    return '<div class="table-wrap">' +
        '<div class="table-surface"></div>' +
        '<div class="table-center">' +
          '<div class="center-label">Round ' + r.round + '</div>' +
          '<div class="center-bid">' + esc(centerBidText) + '</div>' +
          '<div class="' + stakeClass + '">' + mult + ' mouth' + (mult===1?'':'s') + '</div>' +
          (zaiForDisplay ? '<div class="center-zai">ZAI \u2014 1s don\u2019t count</div>' : '') +
        '</div>' +
        seatsHtml +
      '</div>';
  }

  function gameHTML(r){
    if (r.phase === 'gameover') return gameOverHTML(r);
    var me = r.players.find(function(p){ return p.id===myId; });
    var isMyTurn = (r.phase === 'bidding') && r.currentActor === myId;

    var html = '';
    html += '<div class="hud"><span class="round">Round ' + r.round + '</span><span class="code-mini">' + esc(r.code) + '</span></div>';
    if (!me){ html += '<div class="turn-banner theirs">\uD83D\uDC40 You\u2019re spectating</div>'; }

    html += gameTableHTML(r);

    if (r.phase === 'rolling'){
      html += '<div class="panel" style="text-align:center;">' +
        '<div style="color:var(--muted);margin-bottom:12px;">Rolling dice for everyone\u2026</div>' +
        (me ? '<div class="dice-row-real">' + myDice.map(function(d){ return dieHTML(d, flags.rollingAnim ? 'rolling' : ''); }).join('') + '</div>' : '') +
      '</div>';
      return html;
    }

    if (r.phase === 'bidding'){
      var secsLeft = r.turnDeadline ? Math.max(0, Math.ceil((r.turnDeadline - Date.now())/1000)) : null;
      var timerLow = secsLeft !== null && secsLeft <= 10;
      html += '<div class="turn-banner ' + (isMyTurn?'mine':'theirs') + '">' +
        (isMyTurn ? 'Your turn' : (nameOf(r, r.currentActor) + '\u2019s turn')) +
        (secsLeft !== null ? ' <span style="' + (timerLow ? 'color:var(--danger-bright);font-weight:700;' : 'color:var(--muted);') + '">(' + secsLeft + 's)</span>' : '') +
      '</div>';

      html += logHTML(r);
      html += yourHandHTML(me);

      if (isMyTurn){
        var total = totalDiceInPlay(r);
        if (bidQty > total) bidQty = total;
        if (bidQty < 1) bidQty = 1;
        var nb = neighborsOf(r.seating, myId);
        var showPicker = r.seating.length > 2;
        var isReverseChoice = showPicker && r.lastFrom !== null && bidTarget === r.lastFrom;
        var wasZaiActive = !!r.zaiActive;
        var breakingZai = wasZaiActive && bidZaiToggle;
        var proposed = { quantity: bidQty, face: bidFace };
        var valid;
        var zaiMinQty = null;
        var openMinQty = r.currentBid ? null : openingMinQty(r.seating.length, bidFace, bidZaiToggle);
        if (r.currentBid && breakingZai){
          zaiMinQty = r.currentBid.quantity * 2 + (isReverseChoice ? 2 : 0);
          valid = bidQty >= zaiMinQty;
        } else if (r.currentBid && isReverseChoice){
          valid = bidQty >= r.currentBid.quantity + 2;
        } else if (!r.currentBid){
          valid = bidQty >= openMinQty;
        } else {
          valid = isValidBid(r.currentBid, proposed);
        }
        html += '<div class="panel bid-controls">' +
          (showPicker ?
            ('<div class="control-block">' +
              '<div class="label">Pass this bid to</div>' +
              '<div class="row">' +
                '<button class="' + (bidTarget===nb.left?'btn-primary':'btn-secondary') + '" data-action="pick-target" data-target="' + esc(nb.left) + '">' +
                  esc(nameOf(r, nb.left)) + (r.lastFrom===nb.left ? ' (reverse)' : '') +
                '</button>' +
                '<button class="' + (bidTarget===nb.right?'btn-primary':'btn-secondary') + '" data-action="pick-target" data-target="' + esc(nb.right) + '">' +
                  esc(nameOf(r, nb.right)) + (r.lastFrom===nb.right ? ' (reverse)' : '') +
                '</button>' +
              '</div>' +
              (isReverseChoice && !breakingZai ? '<div class="hint bad">Reversing back to ' + esc(nameOf(r, bidTarget)) + ' \u2014 quantity must jump by at least 2.</div>' : '') +
            '</div>') : ''
          ) +
          (r.currentBid ?
            ('<div class="control-block">' +
              '<label class="setting-row" style="cursor:pointer;">' +
                '<input type="checkbox" ' + (bidZaiToggle?'checked':'') + ' data-action="toggle-zai">' +
                '<span>' + (wasZaiActive ?
                  '<strong>Break Zai</strong> \u2014 bring wild Aces back (needs at least double' + (isReverseChoice ? ' + 2 for the reverse' : '') + ')' :
                  '<strong>Call Zai</strong> \u2014 Aces (1s) won\u2019t count on this bid onward') +
                '</span>' +
              '</label>' +
              (breakingZai ? '<div class="hint bad">Breaking Zai \u2014 quantity must be at least ' + zaiMinQty + '.</div>' : '') +
            '</div>') :
            ('<div class="control-block">' +
              '<label class="setting-row" style="cursor:pointer;">' +
                '<input type="checkbox" ' + (bidZaiToggle?'checked':'') + ' data-action="toggle-zai">' +
                '<span><strong>Call Zai</strong> \u2014 Aces (1s) won\u2019t count on this bid onward</span>' +
              '</label>' +
            '</div>')
          ) +
          '<div class="control-block">' +
            '<div class="label">Quantity (of ' + total + ' dice in play)</div>' +
            '<div class="stepper">' +
              '<button data-action="qty-dec">\u2212</button>' +
              '<div class="qty">' + bidQty + '</div>' +
              '<button data-action="qty-inc">+</button>' +
            '</div>' +
          '</div>' +
          '<div class="control-block">' +
            '<div class="label">Face value</div>' +
            '<div class="face-picker">' + [1,2,3,4,5,6].map(faceBtnHTML).join('') + '</div>' +
          '</div>' +
          '<div class="row">' +
            '<button class="btn-primary" data-action="place-bid"' + (valid?'':' disabled') + '>Place bid</button>' +
          '</div>' +
          (r.currentBid ?
            ('<div class="row" style="margin-top:8px;">' +
              '<button class="btn-danger" data-action="challenge">Call Liar! (1\u00d7)</button>' +
              '<button class="btn-danger" data-action="pi" style="background:#7A4FA3;">PI! (2\u00d7)</button>' +
            '</div>') : ''
          ) +
          (!valid && !r.currentBid ? '<div class="hint bad">Opening bid must be at least ' + openMinQty + ' \u00d7 ' + (bidFace===1?'Aces':bidFace) + (bidZaiToggle?' (Zai)':'') + ' with ' + r.seating.length + ' players.</div>' : '') +
          (!valid && r.currentBid && !isReverseChoice && !breakingZai ? '<div class="hint bad">Must beat ' + describeBid(r.currentBid.quantity,r.currentBid.face) + '</div>' : '') +
          (valid && !isReverseChoice && !breakingZai ? ('<div class="hint">' + (wasZaiActive ? 'Zai is active \u2014 Aces (1s) don\u2019t count right now.' : 'Aces (1s) are wild and always count.') + '</div>') : '') +
        '</div>';
      } else {
        html += '<div class="panel" style="text-align:center;color:var(--muted);font-size:0.88rem;">Waiting for ' + esc(nameOf(r, r.currentActor)) + '\u2026</div>';
      }
      return html;
    }

    if (r.phase === 'pi_response'){
      var isResponder = r.challenge && r.challenge.bidderId === myId;
      var secsLeft2 = r.turnDeadline ? Math.max(0, Math.ceil((r.turnDeadline - Date.now())/1000)) : null;
      var timerLow2 = secsLeft2 !== null && secsLeft2 <= 10;
      html += '<div class="turn-banner ' + (isResponder?'mine':'theirs') + '">' +
        (isResponder ? 'You\u2019ve been PI\u2019d!' : (esc(nameOf(r, r.challenge.bidderId)) + ' got PI\u2019d')) +
        (secsLeft2 !== null ? ' <span style="' + (timerLow2 ? 'color:var(--danger-bright);font-weight:700;' : 'color:var(--muted);') + '">(' + secsLeft2 + 's)</span>' : '') +
      '</div>';
      html += '<div class="bid-display">' +
        '<div class="label">' + esc(nameOf(r, r.challenge.challengerId)) + ' called PI on</div>' +
        '<div class="value">' + describeBid(r.challenge.bid.quantity, r.challenge.bid.face) + '</div>' +
        '<div class="by">stakes: 2\u00d7 drinks (accept, or fire back Fan Pi for 4\u00d7)</div>' +
      '</div>';
      html += logHTML(r);
      html += yourHandHTML(me);
      if (isResponder){
        var fanPiOn2 = !r.settings || r.settings.fanPiEnabled !== false;
        html += '<div class="panel">' +
          '<div class="row">' +
            '<button class="btn-secondary" data-action="pi-accept">Accept (2\u00d7)</button>' +
            (fanPiOn2 ? '<button class="btn-danger" data-action="pi-fan" style="background:#7A4FA3;">FAN PI! (4\u00d7)</button>' : '') +
          '</div>' +
        '</div>';
      } else {
        html += '<div class="panel" style="text-align:center;color:var(--muted);font-size:0.88rem;">Waiting for ' + esc(nameOf(r, r.challenge.bidderId)) + ' to respond\u2026</div>';
      }
      return html;
    }

    if (r.phase === 'reveal'){
      html += '<div class="turn-banner theirs">Revealing all dice\u2026</div>';
      html += logHTML(r);
      html += '<div class="reveal-list">';
      r.players.filter(function(p){ return p.alive; }).forEach(function(p){
        var d = r.reveal[p.id];
        html += '<div class="reveal-row"><div class="rname">' + esc(p.name) + (p.id===myId?' (you)':'') + '</div><div class="rdice">' +
          (d ? d.map(function(v){ return dieHTML(v); }).join('') : '<span class="waiting-dots">rolling in\u2026</span>') +
        '</div></div>';
      });
      html += '</div>';
      return html;
    }

    if (r.phase === 'roundend'){
      var lr = r.lastResult;
      var mult = lr.multiplier || 1;
      html += '<div class="result-banner ' + (lr.bidTrue?'true':'false') + '">' +
        '<div class="count-line">' + faceLabel(lr.face) + 's counted: ' + lr.count + ' (bid was ' + lr.quantity + ')</div>' +
        '<div class="sub">' + (lr.bidTrue ? 'The bid was true.' : 'That bid was a bluff.') + ' ' + esc(lr.loserName) + ' drinks ' + mult + (mult===1?'':'\u00d7') + '! \uD83C\uDF7A</div>' +
      '</div>';
      html += '<div class="reveal-list">';
      r.players.forEach(function(p){
        var d = r.reveal[p.id];
        if (!d) return;
        html += '<div class="reveal-row"><div class="rname">' + esc(p.name) + '</div><div class="rdice">' + d.map(function(v){ return dieHTML(v); }).join('') + '</div></div>';
      });
      html += '</div>';
      html += logHTML(r);
      var isHostHere = r.hostId === myId;
      html += '<div class="panel" style="text-align:center;">' +
        '<div style="color:var(--muted);font-size:0.85rem;margin-bottom:10px;">Next round starting soon\u2026</div>' +
        (isHostHere ?
          '<button class="btn-secondary" data-action="continue-now">Start next game</button>' :
          '<div style="color:var(--muted);font-size:0.8rem;">Waiting for the host, or the timer\u2026</div>'
        ) +
      '</div>';
      return html;
    }

    return html;
  }

  function yourHandHTML(me){
    if (!me) return '';
    return '<div class="your-hand"><div class="label"><span>Your dice</span><span>\uD83C\uDF7A\u00d7' + (me.drinks||0) + ' so far</span></div>' +
      '<div class="dice-row-real">' + myDice.map(function(d){ return dieHTML(d); }).join('') + '</div></div>';
  }

  function logHTML(r){
    var items = r.log.slice(-6).reverse().map(function(l){ return '<div>' + esc(l) + '</div>'; }).join('');
    return '<div class="log">' + items + '</div>';
  }

  function gameOverHTML(r){
    var winner = r.players.find(function(p){ return p.id === r.winner; });
    var isHost = r.hostId === myId;
    var html = '<div class="panel">' +
      '<div class="winner-block">' +
        '<div class="trophy">\uD83C\uDFC6</div>' +
        '<h2>' + (winner ? esc(winner.name) + ' wins!' : 'Game over') + '</h2>' +
        '<p>Thanks for playing \u2014 want to run it back?</p>' +
        (isHost ? '<button class="btn-primary" data-action="play-again">Start a new round</button>' :
          '<div style="color:var(--muted);font-size:0.85rem;">Waiting for the host to start a new round\u2026</div>') +
      '</div>' +
    '</div>';
    html += logHTML(r);
    return html;
  }

  function rulesModalHTML(){
    return '<div class="modal-backdrop" data-action="hide-rules">' +
      '<div class="modal" onclick="event.stopPropagation()">' +
        '<h2>How to play</h2>' +
        '<div class="rules-body">' +
          '<p>Everyone starts with 5 dice, rolled in secret. On your turn you either raise the bid or call the previous bidder a liar.</p>' +
          '<h3>Bidding</h3>' +
          '<p>A bid is a claim like \u201cfive 4s\u201d \u2014 a guess about how many dice showing that face exist across <em>everyone\u2019s</em> hands combined, not just your own. Each new bid must raise the quantity, or keep the same quantity and raise the face value.</p>' +
          '<h3>Minimum opening bid</h3>' +
          '<p>The very first bid of each round has a floor that scales with how many are playing: calling Aces needs at least as many as there are players, calling any other face under Zai needs one more than that, and a normal wild-Aces face needs two more than that.</p>' +
          '<h3>Passing around the circle</h3>' +
          '<p>Seating is a circle. When you bid, you also choose which of your two neighbors receives it next \u2014 keep it moving the same way it\u2019s been going, or send it back the way it came. Sending it back is a <strong>reverse</strong>: the quantity must jump by at least 2 (any face value is fine). With only 2 players, there\u2019s just one neighbor, so this doesn\u2019t apply \u2014 normal bidding rules the whole game.</p>' +
          '<h3>Aces are wild</h3>' +
          '<p>Rolled 1s (Aces) count toward any face bid, unless the bid itself is on Aces \u2014 then only actual 1s count.</p>' +
          '<h3>Zai (turning off wild Aces)</h3>' +
          '<p>Any bidder can declare <strong>Zai</strong> on their bid \u2014 from then on, 1s stop being wild and only count for actual Ace bids, until someone breaks it. Breaking Zai (bringing wild Aces back) needs a bid of at least <strong>double</strong> the current quantity. If you\u2019re also reversing direction, add 2 more on top of that double.</p>' +
          '<h3>Calling Liar</h3>' +
          '<p>Instead of bidding, you can call \u201cLiar!\u201d on the previous bid. Everyone\u2019s dice are revealed and counted. If the count meets or beats the bid, the bid holds and the challenger drinks. If it falls short, the bidder was bluffing and drinks instead.</p>' +
          '<h3>PI and Fan Pi (drinking multipliers)</h3>' +
          '<p>Instead of a plain Liar call, you can call <strong>PI</strong> to double the stakes to 2\u00d7. The bidder then gets a choice: <strong>Accept</strong> and keep it at 2\u00d7, or fire back <strong>Fan Pi</strong> to push it to 4\u00d7 (final \u2014 no further escalation). Whoever loses the reveal drinks that many mouthfuls.</p>' +
          '<h3>Turn timer</h3>' +
          '<p>Each turn (and each PI response) has a 60-second limit. If time runs out on a bid, the game auto-calls Liar for you, or auto-places a minimal opening bid if you were meant to open. If time runs out on a PI response, it auto-accepts at 2\u00d7.</p>' +
          '<h3>No elimination \u2014 just for fun</h3>' +
          '<p>Everyone always rolls a fresh 5 dice each round, no matter what happened before. Losing adds to that player\u2019s drink tally (shown next to their name) \u2014 nobody gets knocked out. Play as many rounds as you like, and use \u201cReset table\u201d whenever you want to wrap up. (No pressure to actually drink, either \u2014 the tally works fine as just a scoreboard.)</p>' +
        '</div>' +
        '<button class="btn-secondary" style="margin-top:14px;" data-action="hide-rules">Got it</button>' +
      '</div>' +
    '</div>';
  }

  /* ---------------- actions ---------------- */
  async function handleCreate(){
    errorMsg = '';
    if (!storageAvailable()){
      errorMsg = 'Can\u2019t reach the game server. Make sure the Python server window is still running on the host computer, and that you opened this page using the http://192.168... address it printed.';
      render();
      return;
    }
    var nameEl = document.getElementById('nameInput');
    draftName = (nameEl ? nameEl.value : draftName).trim();
    if (!draftName){ errorMsg = 'Enter your name first.'; render(); return; }
    myName = draftName;
    var attempts = 0;
    var outcome = { status:'conflict' };
    while (attempts < 8 && outcome.status === 'conflict'){
      roomCode = randomCode();
      outcome = await tryCreateRoom(roomCode, myId, myName);
      attempts++;
    }
    if (outcome.status !== 'ok'){
      errorMsg = 'Could not create a table (' + (lastStorageError || 'unknown storage error') + '). Please try again in a moment.';
      render();
      return;
    }
    room = outcome.room;
    myRole = 'player';
    view = 'lobby';
    stopLandingPoll();
    startPolling();
    render();
  }

  async function handleJoin(codeOverride){
    errorMsg = '';
    if (!storageAvailable()){
      errorMsg = 'Can\u2019t reach the game server. Make sure the Python server window is still running on the host computer, and that you opened this page using the http://192.168... address it printed.';
      render();
      return;
    }
    var nameEl = document.getElementById('nameInput');
    draftName = (nameEl ? nameEl.value : draftName).trim();
    var code = codeOverride;
    if (!code){
      var codeEl = document.getElementById('codeInput');
      draftJoinCode = (codeEl ? codeEl.value : draftJoinCode).trim().toUpperCase();
      code = draftJoinCode;
    }
    if (!draftName){ errorMsg = 'Enter your name first.'; render(); return; }
    if (!code || code.length !== 4){ errorMsg = 'Enter the 4-letter table code.'; render(); return; }
    myName = draftName;
    roomCode = code;
    var existing = await getRoomRaw(roomCode);
    if (!existing){ errorMsg = 'No table found with that code.'; render(); return; }
    if (existing.phase !== 'lobby' && !existing.players.find(function(p){ return p.id===myId; })){
      errorMsg = 'That game has already started \u2014 you can watch instead from the table list.'; render(); return;
    }
    var result = await mJoin();
    if (!result){ errorMsg = 'Could not join that table.'; render(); return; }
    room = result;
    myRole = 'player';
    view = 'lobby';
    stopLandingPoll();
    startPolling();
    render();
  }

  async function handleSpectate(code){
    errorMsg = '';
    if (!storageAvailable()){
      errorMsg = 'Can\u2019t reach the game server. Make sure the Python server window is still running on the host computer, and that you opened this page using the http://192.168... address it printed.';
      render();
      return;
    }
    var nameEl = document.getElementById('nameInput');
    draftName = (nameEl ? nameEl.value : draftName).trim();
    if (!draftName){ errorMsg = 'Enter your name first.'; render(); return; }
    myName = draftName;
    roomCode = code;
    var existing = await getRoomRaw(roomCode);
    if (!existing){ errorMsg = 'That table is gone.'; render(); return; }
    if (existing.players.find(function(p){ return p.id===myId; })){
      // Already a seated player at this table -- just go back in as a player.
      room = existing;
      myRole = 'player';
      view = existing.phase === 'lobby' ? 'lobby' : 'game';
      stopLandingPoll();
      startPolling();
      render();
      return;
    }
    var result = await mSpectate(myName);
    if (!result){ errorMsg = 'Could not join as a spectator.'; render(); return; }
    room = result;
    myRole = 'spectator';
    view = result.phase === 'lobby' ? 'lobby' : 'game';
    stopLandingPoll();
    startPolling();
    render();
  }

  function handleClick(e){
    var el = e.target.closest('[data-action]');
    if (!el) return;
    var action = el.dataset.action;
    if (action === 'create') return handleCreate();
    if (action === 'join') return handleJoin();
    if (action === 'browse-join') return handleJoin(el.dataset.code);
    if (action === 'browse-spectate') return handleSpectate(el.dataset.code);
    if (action === 'show-join-code'){ showJoinByCode = true; render(); return; }
    if (action === 'start') return mStart().then(function(r){ if (r) room = r; render(); });
    if (action === 'take-seat'){
      var seatIdx = parseInt(el.dataset.seat, 10);
      return mTakeSeat(seatIdx).then(function(r){ if (r) room = r; render(); });
    }
    if (action === 'add-bot') return mAddBot().then(function(r){ if (r) room = r; render(); });
    if (action === 'remove-bot') return mRemoveBot(el.dataset.id).then(function(r){ if (r) room = r; render(); });
    if (action === 'toggle-fanpi'){
      var current = room && room.settings ? room.settings.fanPiEnabled !== false : true;
      return mUpdateSettings({ fanPiEnabled: !current }).then(function(r){ if (r) room = r; render(); });
    }
    if (action === 'toggle-unlimited-time'){
      var currentUT = room && room.settings ? !!room.settings.unlimitedTime : false;
      return mUpdateSettings({ unlimitedTime: !currentUT }).then(function(r){ if (r) room = r; render(); });
    }
    if (action === 'place-bid') return mPlaceBid(bidQty, bidFace, bidTarget, bidZaiToggle).then(function(r){ bidZaiToggle = false; if (r) { room = r; reactToRoom(r);} render(); });
    if (action === 'toggle-zai'){ bidZaiToggle = !bidZaiToggle; render(); return; }
    if (action === 'continue-now') return mNextRound().then(function(r){ if (r) room = r; render(); });
    if (action === 'challenge') return mChallenge('liar').then(function(r){ if (r) { room = r; reactToRoom(r);} render(); });
    if (action === 'pi') return mChallenge('pi').then(function(r){ if (r) { room = r; reactToRoom(r);} render(); });
    if (action === 'pi-accept') return mRespondPi(false).then(function(r){ if (r) { room = r; reactToRoom(r);} render(); });
    if (action === 'pi-fan') return mRespondPi(true).then(function(r){ if (r) { room = r; reactToRoom(r);} render(); });
    if (action === 'play-again') return mPlayAgain().then(function(r){ if (r) room = r; render(); });
    if (action === 'reset-table'){
      if (confirm('Reset this table back to the lobby for everyone?')){
        mResetTable().then(function(r){ if (r) room = r; render(); });
      }
      return;
    }
    if (action === 'leave'){
      stopPolling();
      view = 'landing'; room = null; roomCode = ''; errorMsg = ''; myRole = 'player';
      render();
      startLandingPoll();
      return;
    }
    if (action === 'show-rules'){ showRules = true; render(); return; }
    if (action === 'hide-rules'){ showRules = false; render(); return; }
    if (action === 'qty-inc'){ var t = room?totalDiceInPlay(room):20; bidQty = Math.min(t, bidQty+1); render(); return; }
    if (action === 'qty-dec'){ bidQty = Math.max(1, bidQty-1); render(); return; }
    if (action === 'pick-face'){ bidFace = parseInt(el.dataset.face, 10); render(); return; }
    if (action === 'pick-target'){ bidTarget = el.dataset.target; render(); return; }
  }

  document.getElementById('app').addEventListener('click', handleClick);
  document.getElementById('app').addEventListener('input', function(e){
    if (e.target.id === 'nameInput') draftName = e.target.value;
    if (e.target.id === 'codeInput') draftJoinCode = e.target.value.toUpperCase();
  });

  render();
  startLandingPoll();
})();
</script>
</body>
</html>
"""

ROOM_RE = re.compile(r"^/api/room/([A-Za-z0-9]{1,12})$")
CREATE_RE = re.compile(r"^/api/room/([A-Za-z0-9]{1,12})/create$")
UPDATE_RE = re.compile(r"^/api/room/([A-Za-z0-9]{1,12})/update$")


class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "LiarsDice/1.0"

    def log_message(self, fmt, *args):
        # Keep the console output quiet and readable.
        sys.stderr.write("  [%s] %s\n" % (self.address_string(), fmt % args))

    def _send_json(self, status, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, body_str):
        body = body_str.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self):
        length = int(self.headers.get("Content-Length", 0) or 0)
        raw = self.rfile.read(length) if length > 0 else b"{}"
        try:
            return json.loads(raw.decode("utf-8")) if raw else {}
        except Exception:
            return None

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            self._send_html(INDEX_HTML)
            return
        if path == "/api/rooms":
            with LOCK:
                summaries = []
                for code, room in ROOMS.items():
                    players = room.get("players", [])
                    host = next((p for p in players if p.get("id") == room.get("hostId")), None)
                    summaries.append({
                        "code": code,
                        "hostName": host["name"] if host else "?",
                        "phase": room.get("phase", "lobby"),
                        "playerCount": len(players),
                        "spectatorCount": len(room.get("spectators", [])),
                        "round": room.get("round", 0),
                    })
            self._send_json(200, {"rooms": summaries})
            return
        m = ROOM_RE.match(path)
        if m:
            code = m.group(1).upper()
            with LOCK:
                room = ROOMS.get(code)
            if room is None:
                self._send_json(404, {"error": "not_found"})
            else:
                self._send_json(200, room)
            return
        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        body = self._read_json_body()
        if body is None:
            self._send_json(400, {"error": "bad_json"})
            return

        m = CREATE_RE.match(path)
        if m:
            code = m.group(1).upper()
            with LOCK:
                if code in ROOMS:
                    self._send_json(409, ROOMS[code])
                    return
                room = body
                room["code"] = code
                room["version"] = 1
                ROOMS[code] = room
            self._send_json(201, room)
            return

        m = UPDATE_RE.match(path)
        if m:
            code = m.group(1).upper()
            expected = body.get("expectedVersion")
            new_room = body.get("room")
            if not isinstance(new_room, dict):
                self._send_json(400, {"error": "bad_room"})
                return
            with LOCK:
                cur = ROOMS.get(code)
                if cur is None:
                    self._send_json(404, {"error": "not_found"})
                    return
                if cur.get("version") != expected:
                    self._send_json(409, cur)
                    return
                new_room["code"] = code
                new_room["version"] = cur["version"] + 1
                ROOMS[code] = new_room
            self._send_json(200, new_room)
            return

        self.send_response(404)
        self.end_headers()


def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


def main():
    port = 8000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print("Usage: python liars_dice_server.py [port]")
            sys.exit(1)

    ip = get_local_ip()
    httpd = socketserver.ThreadingTCPServer(("0.0.0.0", port), Handler)
    httpd.daemon_threads = True

    print("=" * 56)
    print(" Liar's Dice server is running!")
    print("=" * 56)
    print("")
    print(" Share THIS link with everyone on your WiFi:")
    print("")
    print("     http://%s:%d" % (ip, port))
    print("")
    print(" (You can open it yourself too, in any browser.)")
    print("")
    print(" Keep this window open while you play.")
    print(" Press Ctrl+C to stop the server when you're done.")
    print("=" * 56)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")


if __name__ == "__main__":
    main()
