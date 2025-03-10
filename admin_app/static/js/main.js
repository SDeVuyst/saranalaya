/**
* Template Name: Append
* Template URL: https://bootstrapmade.com/append-bootstrap-website-template/
* Updated: Aug 07 2024 with Bootstrap v5.3.3
* Author: BootstrapMade.com
* License: https://bootstrapmade.com/license/
*/

(function() {
  "use strict";

  /**
   * Apply .scrolled class to the body as the page is scrolled down
   */
  function toggleScrolled() {
    const selectBody = document.querySelector('body');
    const selectHeader = document.querySelector('#header');
    
    if (!selectHeader.classList.contains('scroll-up-sticky') && 
        !selectHeader.classList.contains('sticky-top') && 
        !selectHeader.classList.contains('fixed-top')) {
        return;
    }

    if (window.scrollY > 100) {
        selectBody.classList.add('scrolled');
        selectHeader.classList.add('color');
    } else {
        selectBody.classList.remove('scrolled');
        selectHeader.classList.remove('color');
    }
  }

  document.addEventListener('scroll', toggleScrolled);
  window.addEventListener('load', toggleScrolled);

  /**
   * Mobile nav toggle
   */
  const mobileNavToggleBtn = document.querySelector('.mobile-nav-toggle');

  function mobileNavToogle() {
    document.querySelector('body').classList.toggle('mobile-nav-active');
    mobileNavToggleBtn.classList.toggle('bi-list');
    mobileNavToggleBtn.classList.toggle('bi-x');
  }
  mobileNavToggleBtn.addEventListener('click', mobileNavToogle);

  /**
   * Hide mobile nav on same-page/hash links
   */
  document.querySelectorAll('#navmenu a').forEach(navmenu => {
    navmenu.addEventListener('click', () => {
      if (document.querySelector('.mobile-nav-active')) {
        mobileNavToogle();
      }
    });

  });

  /**
   * Toggle mobile nav dropdowns
   */
  document.querySelectorAll('.navmenu .toggle-dropdown').forEach(navmenu => {
    navmenu.addEventListener('click', function(e) {
      e.preventDefault();
      this.parentNode.classList.toggle('active');
      this.parentNode.nextElementSibling.classList.toggle('dropdown-active');
      e.stopImmediatePropagation();
    });
  });

  /**
   * Preloader
   */
  const preloader = document.querySelector('#preloader');
  if (preloader) {
    window.addEventListener('load', () => {
      preloader.remove();
    });
  }

  /**
   * Scroll top button
   */
  let scrollTop = document.querySelector('.scroll-top');

  if (scrollTop) {
    function toggleScrollTop() {
      if (scrollTop) {
        window.scrollY > 100 ? scrollTop.classList.add('active') : scrollTop.classList.remove('active');
      }
    }
    scrollTop.addEventListener('click', (e) => {
      e.preventDefault();
      window.scrollTo({
        top: 0,
        behavior: 'smooth'
      });
    });
  
    window.addEventListener('load', toggleScrollTop);
    document.addEventListener('scroll', toggleScrollTop);
  }
  

  /**
   * Animation on scroll function and init
   */
  function aosInit() {
    AOS.init({
      duration: 600,
      easing: 'ease-in-out',
      once: true,
      mirror: false
    });
  }
  window.addEventListener('load', aosInit);

  /**
   * Initiate glightbox
   */
  const glightbox = GLightbox({
    selector: '.glightbox'
  });

  /**
   * Init isotope layout and filters
   */
  document.querySelectorAll('.isotope-layout').forEach(function(isotopeItem) {
    let layout = isotopeItem.getAttribute('data-layout') ?? 'masonry';
    let filter = isotopeItem.getAttribute('data-default-filter') ?? '*';
    let sort = isotopeItem.getAttribute('data-sort') ?? 'original-order';

    let initIsotope;
    imagesLoaded(isotopeItem.querySelector('.isotope-container'), function() {
      initIsotope = new Isotope(isotopeItem.querySelector('.isotope-container'), {
        itemSelector: '.isotope-item',
        layoutMode: layout,
        filter: filter,
        sortBy: sort
      });
    });

    isotopeItem.querySelectorAll('.isotope-filters li').forEach(function(filters) {
      filters.addEventListener('click', function() {
        isotopeItem.querySelector('.isotope-filters .filter-active').classList.remove('filter-active');
        this.classList.add('filter-active');
        initIsotope.arrange({
          filter: this.getAttribute('data-filter')
        });
        if (typeof aosInit === 'function') {
          aosInit();
        }
      }, false);
    });

  });

  /**
   * Frequently Asked Questions Toggle
   */
  document.querySelectorAll('.faq-item h3, .faq-item .faq-toggle').forEach((faqItem) => {
    faqItem.addEventListener('click', () => {
      faqItem.parentNode.classList.toggle('faq-active');
    });
  });


  /**
   * Correct scrolling position upon page load for URLs containing hash links.
   */
  window.addEventListener('load', function(e) {
    if (window.location.hash) {
      if (document.querySelector(window.location.hash)) {
        setTimeout(() => {
          let section = document.querySelector(window.location.hash);
          let scrollMarginTop = getComputedStyle(section).scrollMarginTop;
          window.scrollTo({
            top: section.offsetTop - parseInt(scrollMarginTop),
            behavior: 'smooth'
          });
        }, 100);
      }
    }
  });

  /**
   * Navmenu Scrollspy
   */
  let navmenulinks = document.querySelectorAll('.navmenu a');

  function navmenuScrollspy() {
    let currentPage = window.location.pathname; // Get current path
    let hasLinkSet = false;

    navmenulinks.forEach(navmenulink => {
        let navLinkHref = navmenulink.getAttribute('href');
        if (!navLinkHref) return;

        // Check if it's a full URL or relative link and get the path only
        let navLinkPath = new URL(navLinkHref, window.location.origin).pathname;

        // Normalize both paths for comparison
        navLinkPath = normalizePath(navLinkPath);
        currentPage = normalizePath(currentPage);

        // Check if current page matches the nav link
        if (hasFiveConsecutiveChars(currentPage, navLinkPath)) {
            document.querySelectorAll('.navmenu a.active').forEach(link => link.classList.remove('active'));
            navmenulink.classList.add('active');
            hasLinkSet = true;
        }

        // For scrollspy functionality within the same page
        if (navmenulink.hash) {
            let section = document.querySelector(navmenulink.hash);
            if (!section) return;
            let position = window.scrollY + 200;
            if (position >= section.offsetTop && position <= (section.offsetTop + section.offsetHeight)) {
                document.querySelectorAll('.navmenu a.active').forEach(link => link.classList.remove('active'));
                navmenulink.classList.add('active');
                hasLinkSet = true;
            } else {
                navmenulink.classList.remove('active');
            }
        }
    });

    if ((!hasLinkSet) && currentPage.length < 3) {
        navmenulinks[0].classList.add('active');
    } else if (!hasLinkSet) {
      document.querySelectorAll('.navmenu a.active').forEach(link => link.classList.remove('active'));
    }
  }

  function normalizePath(path) {
    // Remove any leading or trailing slashes for consistent comparison
    path = path.replace(/\/+$/, '').replace(/^\//, '');

    // Remove the first occurrence of a language code pattern like "/en/" or "/nl/" at the start of the path
    return path.replace(/^\/[a-zA-Z]{2}\//, '');
  }

  function hasFiveConsecutiveChars(currentPage, navLinkPath) {
      for (let i = 0; i <= navLinkPath.length - 5; i++) {
          let substring = navLinkPath.substring(i, i + 5);
          if (currentPage.includes(substring)) {
              return true;
          }
      }
      return false;
  }

  window.addEventListener('load', navmenuScrollspy);
  document.addEventListener('scroll', navmenuScrollspy);

})();