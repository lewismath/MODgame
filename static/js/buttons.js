const Buttons = (() => {
  const BUTTON_DEFS = [
    { action: 'spread_spreadable_influencer', label: 'Spread\nSpreadable\nInfluencer' },
    { action: 'spread_spreadable_connector',  label: 'Spread\nSpreadable\nConnector'  },
    { action: 'spread_persuasive_influencer', label: 'Spread\nPersuasive\nInfluencer' },
    { action: 'spread_persuasive_connector',  label: 'Spread\nPersuasive\nConnector'  },
    { action: 'discredit_highdegree',         label: 'Discredit\nHub'                 },
    { action: 'discredit_highbetweenness',    label: 'Discredit\nBridge'              },
  ];

  // Maps action string -> {btn, bar} elements, per player
  const refs = { red: {}, blue: {} };

  function init(onAction) {
    _build('red', 'buttons-red', onAction);
    _build('blue', 'buttons-blue', onAction);
  }

  function _build(player, containerId, onAction) {
    const container = document.getElementById(containerId);
    container.innerHTML = '';
    BUTTON_DEFS.forEach(({ action, label }) => {
      const btn = document.createElement('button');
      btn.className = `action-btn ${player}-btn`;
      btn.innerHTML = label.replace(/\n/g, '<br>');

      const bar = document.createElement('div');
      bar.className = 'cooldown-bar';
      btn.appendChild(bar);

      btn.addEventListener('click', () => {
        if (!btn.disabled) onAction(player, action);
      });

      container.appendChild(btn);
      refs[player][action] = { btn, bar };
    });
  }

  function updateCooldowns(cooldowns) {
    // cooldowns: { red: { action: seconds_remaining, ... }, blue: { ... } }
    ['red', 'blue'].forEach(player => {
      const cd = cooldowns[player] || {};
      Object.entries(cd).forEach(([action, remaining]) => {
        const ref = refs[player][action];
        if (!ref) return;
        const { btn, bar } = ref;
        const totalCooldown = 10.0; // matches COOLDOWN_DURATIONS on server
        const fraction = Math.min(1, remaining / totalCooldown);
        bar.style.width = `${fraction * 100}%`;
        btn.disabled = remaining > 0;
      });
    });
  }

  return { init, updateCooldowns };
})();
