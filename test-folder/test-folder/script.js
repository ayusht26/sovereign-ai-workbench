// Image Slideshow Script
document.addEventListener('DOMContentLoaded', function() {
    const slideshowContainer = document.getElementById('slideshow');
    const slides = document.querySelectorAll('.slide');
    let currentIndex = 0;
    
    // Get all slide images from data sources
    const imageSources = [
        'https://picsum.photos/800/600?random=1',
        'https://picsum.photos/800/600?random=2',
        'https://picsum.photos/800/600?random=3',
        'https://picsum.photos/800/600?random=4',
        'https://picsum.photos/800/600?random=5'
    ];
    
    // Initialize slideshow with images
    function initializeSlideshow() {
        slides.forEach((slide, index) => {
            slide.style.backgroundImage = `url('${imageSources[index]}')`;
            if (index === 0) {
                showSlide(index);
            }
        });
    }
    
    // Show a specific slide
    function showSlide(index) {
        slides.forEach(slide => {
            slide.classList.remove('active');
            slide.style.opacity = '0';
        });
        
        const currentSlide = slides[index];
        currentSlide.classList.add('active');
        
        // Fade in animation
        animateFadeIn(currentSlide);
    }
    
    // Fade-in animation for slides
    function animateFadeIn(slide) {
        slide.style.transition = 'opacity 1s ease-in-out';
        slide.style.opacity = '1';
    }
    
    // Auto-advance slideshow
    setInterval(() => {
        currentIndex = (currentIndex + 1) % imageSources.length;
        showSlide(currentIndex);
    }, 5000); // Change slide every 5 seconds
    
    // Keyboard navigation
    document.addEventListener('keydown', function(e) {
        if (e.key === 'ArrowLeft') {
            currentIndex = Math.max(0, currentIndex - 1);
            showSlide(currentIndex);
        } else if (e.key === 'ArrowRight') {
            currentIndex = Math.min(slides.length - 1, currentIndex + 1);
            showSlide(currentIndex);
        } else if (e.key === ' ' || e.key === 'Enter') {
            // Pause on space/enter
            pauseSlideshow();
        }
    });
    
    // Touch/swipe support for mobile
    let touchStartX = 0;
    let touchEndX = 0;
    
    slideshowContainer.addEventListener('touchstart', function(e) {
        touchStartX = e.touches[0].clientX;
    });
    
    slideshowContainer.addEventListener('touchend', function(e) {
        touchEndX = e.changedTouches[0].clientX;
        
        if (touchStartX - touchEndX > 100) {
            // Swipe left - go to next slide
            currentIndex = Math.min(slides.length - 1, currentIndex + 1);
            showSlide(currentIndex);
        } else if (touchEndX - touchStartX > 100) {
            // Swipe right - go to previous slide
            currentIndex = Math.max(0, currentIndex - 1);
            showSlide(currentIndex);
        }
    });
    
    // Start slideshow
    initializeSlideshow();
});
