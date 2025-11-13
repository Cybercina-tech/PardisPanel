document.addEventListener('DOMContentLoaded', () => {
    const html = document.documentElement;
    html.classList.add('js-ready');

    const navbar = document.getElementById('mainNavbar');
    const toggleNavbarState = () => {
        if (!navbar) return;
        const shouldCompact = window.scrollY > 12;
        navbar.classList.toggle('scrolled', shouldCompact);
    };

    toggleNavbarState();
    window.addEventListener('scroll', toggleNavbarState, { passive: true });

    const body = document.body;
    if (!body) return;

    const enableKeyboardFocus = (event) => {
        if (event.key !== 'Tab') return;
        body.classList.add('uses-keyboard');
        body.classList.remove('uses-pointer');
        window.removeEventListener('keydown', enableKeyboardFocus);
        window.addEventListener('mousedown', enablePointerFocus, { once: true });
    };

    const enablePointerFocus = () => {
        body.classList.add('uses-pointer');
        body.classList.remove('uses-keyboard');
        window.addEventListener('keydown', enableKeyboardFocus, { once: true });
    };

    body.classList.add('uses-pointer');
    window.addEventListener('keydown', enableKeyboardFocus, { once: true });
});
