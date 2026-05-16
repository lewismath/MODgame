(() => {
  const socket = io();

  const startScreen = document.getElementById('start-screen');
  const startBtn = document.getElementById('start-btn');
  const overlay = document.getElementById('overlay');
  const winnerText = document.getElementById('winner-text');
  const finalScores = document.getElementById('final-scores');
  const playAgain = document.getElementById('play-again');
  const timerEl = document.getElementById('timer');
  const scoreRed = document.getElementById('score-red');
  const scoreBlue = document.getElementById('score-blue');

  Buttons.init((player, action) => {
    socket.emit('action', { player, action });
  });

  startBtn.addEventListener('click', () => {
    socket.emit('start_game');
    startScreen.style.display = 'none';
  });

  playAgain.addEventListener('click', () => {
    overlay.classList.add('hidden');
    startScreen.style.display = 'flex';
  });

  socket.on('game_init', ({ network, initial_states, duration }) => {
    Network.init(network);
    Network.update(initial_states);
  });

  socket.on('state', ({ node_states, scores, time_remaining, cooldowns }) => {
    Network.update(node_states);
    Buttons.updateCooldowns(cooldowns);

    scoreRed.textContent = `RED: ${scores.red}`;
    scoreBlue.textContent = `BLUE: ${scores.blue}`;

    const mins = Math.floor(time_remaining / 60);
    const secs = Math.floor(time_remaining % 60).toString().padStart(2, '0');
    timerEl.textContent = `${mins}:${secs}`;
  });

  socket.on('action_result', ({ removed_edges }) => {
    if (removed_edges && removed_edges.length > 0) {
      Network.removeEdges(removed_edges);
    }
  });

  socket.on('game_over', ({ red, blue, S, winner }) => {
    winnerText.textContent = `${winner.toUpperCase()} WINS`;
    winnerText.style.color = winner === 'red' ? '#e84040' : '#4080e8';
    finalScores.textContent = `Red: ${red}  |  Blue: ${blue}  |  Neutral: ${S}`;
    overlay.classList.remove('hidden');
  });
})();
