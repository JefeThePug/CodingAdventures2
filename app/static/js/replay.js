const gif = document.getElementById('gif');
const replayBtn = document.getElementById('replay-btn');

replayBtn.addEventListener('click', () => {
    const clone = gif.cloneNode(true);
    gif.replaceWith(clone);
});
