(function () {
    function closeNav() {
        var menu = document.getElementById('menu');
        if (menu) menu.classList.remove('active');
        document.querySelectorAll('.menu-item.active, .has-submenu.active').forEach(function (el) {
            el.classList.remove('active');
        });
    }
    document.addEventListener('DOMContentLoaded', closeNav);
    window.addEventListener('pageshow', function (e) {
        if (e.persisted) closeNav();
    });
})();
