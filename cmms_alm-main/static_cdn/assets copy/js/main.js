/**
* Template Name: NiceAdmin
* Updated: Sep 18 2023 with Bootstrap v5.3.2
* Template URL: https://bootstrapmade.com/nice-admin-bootstrap-admin-html-template/
* Author: BootstrapMade.com
* License: https://bootstrapmade.com/license/
*/

console.log("main.js is loaded!");

(function() {
  "use strict";

  /**
   * Easy selector helper function
   */
  const select = (el, all = false) => {
    el = el.trim()
    if (all) {
      return [...document.querySelectorAll(el)]
    } else {
      return document.querySelector(el)
    }
  }

  /**
   * Easy event listener function
   */
  const on = (type, el, listener, all = false) => {
    if (all) {
      select(el, all).forEach(e => e.addEventListener(type, listener))
    } else {
      select(el, all).addEventListener(type, listener)
    }
  }

  /**
   * Easy on scroll event listener 
   */
  const onscroll = (el, listener) => {
    el.addEventListener('scroll', listener)
  }

  /**
   * Sidebar toggle
   */
  if (select('.toggle-sidebar-btn')) {
    on('click', '.toggle-sidebar-btn', function(e) {
      select('body').classList.toggle('toggle-sidebar')
    })
  }

  /**
   * Search bar toggle
   */
  if (select('.search-bar-toggle')) {
    on('click', '.search-bar-toggle', function(e) {
      select('.search-bar').classList.toggle('search-bar-show')
    })
  }

  /**
   * Navbar links active state on scroll
   */
  let navbarlinks = select('#navbar .scrollto', true)
  const navbarlinksActive = () => {
    let position = window.scrollY + 200
    navbarlinks.forEach(navbarlink => {
      if (!navbarlink.hash) return
      let section = select(navbarlink.hash)
      if (!section) return
      if (position >= section.offsetTop && position <= (section.offsetTop + section.offsetHeight)) {
        navbarlink.classList.add('active')
      } else {
        navbarlink.classList.remove('active')
      }
    })
  }
  window.addEventListener('load', navbarlinksActive)
  onscroll(document, navbarlinksActive)

  /**
   * Toggle .header-scrolled class to #header when page is scrolled
   */
  let selectHeader = select('#header')
  if (selectHeader) {
    const headerScrolled = () => {
      if (window.scrollY > 100) {
        selectHeader.classList.add('header-scrolled')
      } else {
        selectHeader.classList.remove('header-scrolled')
      }
    }
    window.addEventListener('load', headerScrolled)
    onscroll(document, headerScrolled)
  }

  /**
   * Back to top button
   */
  let backtotop = select('.back-to-top')
  if (backtotop) {
    const toggleBacktotop = () => {
      if (window.scrollY > 100) {
        backtotop.classList.add('active')
      } else {
        backtotop.classList.remove('active')
      }
    }
    window.addEventListener('load', toggleBacktotop)
    onscroll(document, toggleBacktotop)
  }

  /**
   * Initiate tooltips
   */
  var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
  var tooltipList = tooltipTriggerList.map(function(tooltipTriggerEl) {
    return new bootstrap.Tooltip(tooltipTriggerEl)
  })

  /**
   * Initiate quill editors
   */
  if (select('.quill-editor-default')) {
    new Quill('.quill-editor-default', {
      theme: 'snow'
    });
  }

  if (select('.quill-editor-bubble')) {
    new Quill('.quill-editor-bubble', {
      theme: 'bubble'
    });
  }

  if (select('.quill-editor-full')) {
    new Quill(".quill-editor-full", {
      modules: {
        toolbar: [
          [{
            font: []
          }, {
            size: []
          }],
          ["bold", "italic", "underline", "strike"],
          [{
              color: []
            },
            {
              background: []
            }
          ],
          [{
              script: "super"
            },
            {
              script: "sub"
            }
          ],
          [{
              list: "ordered"
            },
            {
              list: "bullet"
            },
            {
              indent: "-1"
            },
            {
              indent: "+1"
            }
          ],
          ["direction", {
            align: []
          }],
          ["link", "image", "video"],
          ["clean"]
        ]
      },
      theme: "snow"
    });
  }

  /**
   * Initiate TinyMCE Editor
   */
  const useDarkMode = window.matchMedia('(prefers-color-scheme: dark)').matches;
  const isSmallScreen = window.matchMedia('(max-width: 1023.5px)').matches;

  tinymce.init({
    selector: 'textarea.tinymce-editor',
    plugins: 'preview importcss searchreplace autolink autosave save directionality code visualblocks visualchars fullscreen image link media template codesample table charmap pagebreak nonbreaking anchor insertdatetime advlist lists wordcount help charmap quickbars emoticons',
    editimage_cors_hosts: ['picsum.photos'],
    menubar: 'file edit view insert format tools table help',
    toolbar: 'undo redo | bold italic underline strikethrough | fontfamily fontsize blocks | alignleft aligncenter alignright alignjustify | outdent indent |  numlist bullist | forecolor backcolor removeformat | pagebreak | charmap emoticons | fullscreen  preview save print | insertfile image media template link anchor codesample | ltr rtl',
    toolbar_sticky: true,
    toolbar_sticky_offset: isSmallScreen ? 102 : 108,
    autosave_ask_before_unload: true,
    autosave_interval: '30s',
    autosave_prefix: '{path}{query}-{id}-',
    autosave_restore_when_empty: false,
    autosave_retention: '2m',
    image_advtab: true,
    link_list: [{
        title: 'My page 1',
        value: 'https://www.tiny.cloud'
      },
      {
        title: 'My page 2',
        value: 'http://www.moxiecode.com'
      }
    ],
    image_list: [{
        title: 'My page 1',
        value: 'https://www.tiny.cloud'
      },
      {
        title: 'My page 2',
        value: 'http://www.moxiecode.com'
      }
    ],
    image_class_list: [{
        title: 'None',
        value: ''
      },
      {
        title: 'Some class',
        value: 'class-name'
      }
    ],
    importcss_append: true,
    file_picker_callback: (callback, value, meta) => {
      /* Provide file and text for the link dialog */
      if (meta.filetype === 'file') {
        callback('https://www.google.com/logos/google.jpg', {
          text: 'My text'
        });
      }

      /* Provide image and alt text for the image dialog */
      if (meta.filetype === 'image') {
        callback('https://www.google.com/logos/google.jpg', {
          alt: 'My alt text'
        });
      }

      /* Provide alternative source and posted for the media dialog */
      if (meta.filetype === 'media') {
        callback('movie.mp4', {
          source2: 'alt.ogg',
          poster: 'https://www.google.com/logos/google.jpg'
        });
      }
    },
    templates: [{
        title: 'New Table',
        description: 'creates a new table',
        content: '<div class="mceTmpl"><table width="98%%"  border="0" cellspacing="0" cellpadding="0"><tr><th scope="col"> </th><th scope="col"> </th></tr><tr><td> </td><td> </td></tr></table></div>'
      },
      {
        title: 'Starting my story',
        description: 'A cure for writers block',
        content: 'Once upon a time...'
      },
      {
        title: 'New list with dates',
        description: 'New List with dates',
        content: '<div class="mceTmpl"><span class="cdate">cdate</span><br><span class="mdate">mdate</span><h2>My List</h2><ul><li></li><li></li></ul></div>'
      }
    ],
    template_cdate_format: '[Date Created (CDATE): %m/%d/%Y : %H:%M:%S]',
    template_mdate_format: '[Date Modified (MDATE): %m/%d/%Y : %H:%M:%S]',
    height: 600,
    image_caption: true,
    quickbars_selection_toolbar: 'bold italic | quicklink h2 h3 blockquote quickimage quicktable',
    noneditable_class: 'mceNonEditable',
    toolbar_mode: 'sliding',
    contextmenu: 'link image table',
    skin: useDarkMode ? 'oxide-dark' : 'oxide',
    content_css: useDarkMode ? 'dark' : 'default',
    content_style: 'body { font-family:Helvetica,Arial,sans-serif; font-size:16px }'
  });

  /**
   * Initiate Bootstrap validation check
   */
  var needsValidation = document.querySelectorAll('.needs-validation')

  Array.prototype.slice.call(needsValidation)
    .forEach(function(form) {
      form.addEventListener('submit', function(event) {
        if (!form.checkValidity()) {
          event.preventDefault()
          event.stopPropagation()
        }

        form.classList.add('was-validated')
      }, false)
    })

  /**
   * Initiate Datatables
   */
  const datatables = select('.datatable', true)
  datatables.forEach(datatable => {
    new simpleDatatables.DataTable(datatable);
  })

  /**
   * Autoresize echart charts
   */
  const mainContainer = select('#main');
  if (mainContainer) {
    setTimeout(() => {
      new ResizeObserver(function() {
        select('.echart', true).forEach(getEchart => {
          echarts.getInstanceByDom(getEchart).resize();
        })
      }).observe(mainContainer);
    }, 200);
  }

})();

// Javascript Logic for Work Calendar
// try {
//   document.addEventListener("DOMContentLoaded", function() {
//     // Initialize the calendar
//     const calendar = new tui.Calendar('#calendar', {
//         defaultView: 'month',
//         taskView: true,
//         scheduleView: true,
//         useDetailPopup: true,  // Enables a popup to show details on click
//     });

//     // Event listener for date clicks
//     calendar.createEvents([
//       {
//         id: 'event1',
//         calendarId: 'cal2',
//         title: 'Weekly meeting',
//         start: '2022-06-07T09:00:00',
//         end: '2022-06-07T10:00:00',
//       },
//       {
//         id: 'event2',
//         calendarId: 'cal1',
//         title: 'Lunch appointment',
//         start: '2022-06-08T12:00:00',
//         end: '2022-06-08T13:00:00',
//       },
//       {
//         id: 'event3',
//         calendarId: 'cal2',
//         title: 'Vacation',
//         start: '2022-06-08',
//         end: '2022-06-10',
//         isAllday: true,
//         category: 'allday',
//       },
//     ]);
// });

// } catch (error) {
//   console.log(error)
// }

// Javascript Logic for Work request
try {
  //Toggle Subcategory Sidebar

document.addEventListener('DOMContentLoaded', () => {
  const sidebarContent = document.querySelector('.workRequest-sidebar_contents');
  const workRequestContent = document.querySelector('.workRequest-body_content');
  const defaultImage = document.getElementById('default-image')
  const loadMoreBtn = document.getElementById('loadMoreBtn');
const workRequestCount = document.getElementById('workRequestCount');

  let workRequestSidebar = document.querySelector(".workRequest-sidebar");
let workRequestSidebarBtn = document.querySelector(".workRequest-sidebarBtn");

workRequestSidebarBtn.addEventListener('click', () => {
  workRequestSidebar.classList.toggle('active');
})




  const workRequestDetails = {
    1:{
      number: "0033933",
      createdDate: "20/09/2024",
      workNumber: "#0005700",
      type: "Unplanned",
      facility: "PMI SENEGAL",
      category: "Payment Request",
      subcategory: "Payment Request",
      priority: "Normal",
      title: "Payment Request",
      description: "PAYMENT REQUEST FOR PMI SGL: Please pay DIPROTEC XOF 147 500 for purchase softener salt",
      name: "Fanta Guerineau",
      phone: "221776443634",
      email: "fanta.guerineau@alphamead.com",
      startDate: "20/09/2024",
      startTime: "02:25 PM",
      imprest: "No",
      fee: "No",
      approve: "Yes",
      po: "No",
      status: "Open"
    },

    2:{
      number: "0033933",
      createdDate: "20/09/2024",
      workNumber: "#0005700",
      type: "Unplanned",
      facility: "PMI SENEGAL",
      category: "Payment Request",
      subcategory: "Payment Request",
      priority: "Normal",
      title: "Payment Request",
      description: "PAYMENT REQUEST FOR PMI SGL: Please pay DIPROTEC XOF 147 500 for purchase softener salt",
      name: "Fanta Guerineau",
      phone: "221776443634",
      email: "fanta.guerineau@alphamead.com",
      startDate: "20/09/2024",
      startTime: "02:25 PM",
      imprest: "No",
      fee: "No",
      approve: "Yes",
      po: "No",
      status: "Open"
    },

    3:{
      number: "0033933",
      createdDate: "20/09/2024",
      workNumber: "#0005700",
      type: "Unplanned",
      facility: "PMI SENEGAL",
      category: "Payment Request",
      subcategory: "Payment Request",
      priority: "Normal",
      title: "Payment Request",
      description: "PAYMENT REQUEST FOR PMI SGL: Please pay DIPROTEC XOF 147 500 for purchase softener salt",
      name: "Fanta Guerineau",
      phone: "221776443634",
      email: "fanta.guerineau@alphamead.com",
      startDate: "20/09/2024",
      startTime: "02:25 PM",
      imprest: "No",
      fee: "No",
      approve: "Yes",
      po: "No",
      status: "Open"
    },

    4:{
      number: "0033933",
      createdDate: "20/09/2024",
      workNumber: "#0005700",
      type: "Unplanned",
      facility: "PMI SENEGAL",
      category: "Payment Request",
      subcategory: "Payment Request",
      priority: "Normal",
      title: "Payment Request",
      description: "PAYMENT REQUEST FOR PMI SGL: Please pay DIPROTEC XOF 147 500 for purchase softener salt",
      name: "Fanta Guerineau",
      phone: "221776443634",
      email: "fanta.guerineau@alphamead.com",
      startDate: "20/09/2024",
      startTime: "02:25 PM",
      imprest: "No",
      fee: "No",
      approve: "Yes",
      po: "No",
      status: "Open"
    },

    5:{
      number: "0033933",
      createdDate: "20/09/2024",
      workNumber: "#0005700",
      type: "Unplanned",
      facility: "PMI SENEGAL",
      category: "Payment Request",
      subcategory: "Payment Request",
      priority: "Normal",
      title: "Payment Request",
      description: "PAYMENT REQUEST FOR PMI SGL: Please pay DIPROTEC XOF 147 500 for purchase softener salt",
      name: "Fanta Guerineau",
      phone: "221776443634",
      email: "fanta.guerineau@alphamead.com",
      startDate: "20/09/2024",
      startTime: "02:25 PM",
      imprest: "No",
      fee: "No",
      approve: "Yes",
      po: "No",
      status: "Open"
    },

    6:{
      number: "0033933",
      createdDate: "20/09/2024",
      workNumber: "#0005700",
      type: "Unplanned",
      facility: "PMI SENEGAL",
      category: "Payment Request",
      subcategory: "Payment Request",
      priority: "Normal",
      title: "Payment Request",
      description: "PAYMENT REQUEST FOR PMI SGL: Please pay DIPROTEC XOF 147 500 for purchase softener salt",
      name: "Fanta Guerineau",
      phone: "221776443634",
      email: "fanta.guerineau@alphamead.com",
      startDate: "20/09/2024",
      startTime: "02:25 PM",
      imprest: "No",
      fee: "No",
      approve: "Yes",
      po: "No",
      status: "Open"
    },

    7:{
      number: "0033933",
      createdDate: "20/09/2024",
      workNumber: "#0005700",
      type: "Unplanned",
      facility: "PMI SENEGAL",
      category: "Payment Request",
      subcategory: "Payment Request",
      priority: "Normal",
      title: "Payment Request",
      description: "PAYMENT REQUEST FOR PMI SGL: Please pay DIPROTEC XOF 147 500 for purchase softener salt",
      name: "Fanta Guerineau",
      phone: "221776443634",
      email: "fanta.guerineau@alphamead.com",
      startDate: "20/09/2024",
      startTime: "02:25 PM",
      imprest: "No",
      fee: "No",
      approve: "Yes",
      po: "No",
      status: "Open"
    },

    8:{
      number: "0033933",
      createdDate: "20/09/2024",
      workNumber: "#0005700",
      type: "Unplanned",
      facility: "PMI SENEGAL",
      category: "Payment Request",
      subcategory: "Payment Request",
      priority: "Normal",
      title: "Payment Request",
      description: "PAYMENT REQUEST FOR PMI SGL: Please pay DIPROTEC XOF 147 500 for purchase softener salt",
      name: "Fanta Guerineau",
      phone: "221776443634",
      email: "fanta.guerineau@alphamead.com",
      startDate: "20/09/2024",
      startTime: "02:25 PM",
      imprest: "No",
      fee: "No",
      approve: "Yes",
      po: "No",
      status: "Open"
    },

    9:{
      number: "0033933",
      createdDate: "20/09/2024",
      workNumber: "#0005700",
      type: "Unplanned",
      facility: "PMI SENEGAL",
      category: "Payment Request",
      subcategory: "Payment Request",
      priority: "Normal",
      title: "Payment Request",
      description: "PAYMENT REQUEST FOR PMI SGL: Please pay DIPROTEC XOF 147 500 for purchase softener salt",
      name: "Fanta Guerineau",
      phone: "221776443634",
      email: "fanta.guerineau@alphamead.com",
      startDate: "20/09/2024",
      startTime: "02:25 PM",
      imprest: "No",
      fee: "No",
      approve: "Yes",
      po: "No",
      status: "Open"
    },

    10:{
      number: "0033933",
      createdDate: "20/09/2024",
      workNumber: "#0005700",
      type: "Unplanned",
      facility: "PMI SENEGAL",
      category: "Payment Request",
      subcategory: "Payment Request",
      priority: "Normal",
      title: "Payment Request",
      description: "PAYMENT REQUEST FOR PMI SGL: Please pay DIPROTEC XOF 147 500 for purchase softener salt",
      name: "Fanta Guerineau",
      phone: "221776443634",
      email: "fanta.guerineau@alphamead.com",
      startDate: "20/09/2024",
      startTime: "02:25 PM",
      imprest: "No",
      fee: "No",
      approve: "Yes",
      po: "No",
      status: "Open"
    },

  11:{
      number: "0033933",
      createdDate: "20/09/2024",
      workNumber: "#0005700",
      type: "Unplanned",
      facility: "PMI SENEGAL",
      category: "Payment Request",
      subcategory: "Payment Request",
      priority: "Normal",
      title: "Payment Request",
      description: "PAYMENT REQUEST FOR PMI SGL: Please pay DIPROTEC XOF 147 500 for purchase softener salt",
      name: "Fanta Guerineau",
      phone: "221776443634",
      email: "fanta.guerineau@alphamead.com",
      startDate: "20/09/2024",
      startTime: "02:25 PM",
      imprest: "No",
      fee: "No",
      approve: "Yes",
      po: "No",
      status: "Open"
    },

    
  };


  const displayItemDetails = (details) => {
    document.getElementById('number').innerText = details.number
    document.getElementById('created-date').innerText = details.createdDate;
    document.getElementById('work-no').innerText = details.workNumber;
    document.getElementById('type').innerText = details.type;
    document.getElementById('facility').innerText = details.facility;
    document.getElementById('category').innerText = details.category;
    document.getElementById('sub-category').innerText = details.subcategory;
    document.getElementById('priority').innerText = details.priority;
    document.getElementById('title').innerText = details.title;
    document.getElementById('description').innerText = details.description;
    document.getElementById('names').innerText = details.name;
    document.getElementById('phone').innerText = details.phone;
    document.getElementById('email').innerText = details.email;
    document.getElementById('start-date').innerText = details.startDate;
    document.getElementById('start-time').innerText = details.startTime;
    document.getElementById('imprest').innerText = details.imprest;
    document.getElementById('mob-fee').innerText = details.fee;
    document.getElementById('approve').innerText = details.approve;
    document.getElementById('p-o').innerText = details.po;
    document.getElementById('status').innerText = details.status;
  }
  
  sidebarContent.addEventListener('click', (event) => {
    const clickedItem = event.target.closest('.workRequest-sidebar_content');
    if (clickedItem) {
      const itemId = clickedItem.dataset.id;
      const details = workRequestDetails[itemId];
      if (details) {
        defaultImage.style.display = 'none';
        workRequestContent.style.display = 'block';
        displayItemDetails(details);
      }
    }
  });

  // Sample data to mimic multiple work order items
const workRequests = [
  { id: 1, name: '0033933', description: 'Payment Request', status: 'Open' },
  { id: 2, name: '0033932', description: 'Payment Request', status: 'Open' },
  { id: 3, name: '0033931', description: 'Payment Request', status: 'Open' },
  { id: 4, name: '0033930', description: 'Waste management', status: 'New' },
  { id: 5, name: '0033929', description: 'Security Services', status: 'New' },
  { id: 6, name: '0033928', description: 'Maintenance', status: 'Pending' },
  { id: 7, name: '0033927', description: 'IT Support', status: 'Completed' },
  { id: 8, name: '0033926', description: 'Cleaning Services', status: 'In Progress' },
  { id: 9, name: '0033925', description: 'Security Services', status: 'New' },
  { id: 10, name: '0033924', description: 'Network Installation', status: 'Completed' },
  { id: 11, name: '0033923', description: 'Plumbing Work', status: 'In Progress' },
  { id: 12, name: '0033922', description: 'Electrical Work', status: 'Open' }
];

// Number of work orders to show initially
let workRequestsToShow = 10;




// Function to render work orders
function renderWorkRequests() {
  // Clear current contents
  sidebarContent.innerHTML = '';
  

  // Render the number of work orders specified by workRequestsToShow
  workRequests.slice(0, workRequestsToShow).forEach(order => {
    const content = `
      <div class="workRequest-sidebar_content" data-id="${order.id}">
        <div class="workRequest-name">
          <span>${order.name}</span>
          <h6>${order.description}</h6>
        </div>
        <div class="workRequest-status">
          <h6>${order.description}</h6>
          <h6>${order.status}</h6>
        </div>
      </div>
    `;
    sidebarContent.insertAdjacentHTML('beforeend', content);
  });
  workRequestCount.textContent = `Showing 1 - ${workRequestsToShow} of ${workRequests.length}`;

  sidebarContent.scrollTop = sidebarContent.scrollHeight - previousScrollHeight;
}

// Event listener for the "Load More" button
loadMoreBtn.addEventListener('click', () => {
  // Increase the number of work orders to show by 5
  workRequestsToShow += 5;

  // If the number of work orders to show exceeds the total, hide the button
  if (workRequestsToShow >= workRequests.length) {
    workRequestsToShow = workRequests.length;
    // loadMoreBtn.style.display = 'none';
  }

  // Render the updated work orders
  renderWorkRequests();
});

// Initial render
renderWorkRequests();

})
} catch (error) {
  console.log(error)
}

// Javascript Logic for Work order
try {
  //Toggle Subcategory Sidebar

document.addEventListener('DOMContentLoaded', () => {
  const sidebarContent = document.querySelector('.workOrder-sidebar_contents');
  const workOrderContent = document.querySelector('.workOrder-body_content');
  const defaultImage = document.getElementById('default-image')
  const loadMoreBtn = document.getElementById('loadMoreBtn');
const workOrderCount = document.getElementById('workOrderCount');

  let workOrderSidebar = document.querySelector(".workOrder-sidebar");
let workOrderSidebarBtn = document.querySelector(".workOrder-sidebarBtn");

workOrderSidebarBtn.addEventListener('click', () => {
  workOrderSidebar.classList.toggle('active');
})




  const workOrderDetails = {
    1:{
      number: "0033933",
      createdDate: "20/09/2024",
      workNumber: "#0005700",
      type: "Unplanned",
      facility: "PMI SENEGAL",
      category: "Payment Request",
      subcategory: "Payment Request",
      priority: "Normal",
      title: "Payment Request",
      description: "PAYMENT REQUEST FOR PMI SGL: Please pay DIPROTEC XOF 147 500 for purchase softener salt",
      name: "Fanta Guerineau",
      phone: "221776443634",
      email: "fanta.guerineau@alphamead.com",
      startDate: "20/09/2024",
      startTime: "02:25 PM",
      imprest: "No",
      fee: "No",
      approve: "Yes",
      po: "No",
      status: "Open"
    },

    2:{
      number: "0033933",
      createdDate: "20/09/2024",
      workNumber: "#0005700",
      type: "Unplanned",
      facility: "PMI SENEGAL",
      category: "Payment Request",
      subcategory: "Payment Request",
      priority: "Normal",
      title: "Payment Request",
      description: "PAYMENT REQUEST FOR PMI SGL: Please pay DIPROTEC XOF 147 500 for purchase softener salt",
      name: "Fanta Guerineau",
      phone: "221776443634",
      email: "fanta.guerineau@alphamead.com",
      startDate: "20/09/2024",
      startTime: "02:25 PM",
      imprest: "No",
      fee: "No",
      approve: "Yes",
      po: "No",
      status: "Open"
    },

    3:{
      number: "0033933",
      createdDate: "20/09/2024",
      workNumber: "#0005700",
      type: "Unplanned",
      facility: "PMI SENEGAL",
      category: "Payment Request",
      subcategory: "Payment Request",
      priority: "Normal",
      title: "Payment Request",
      description: "PAYMENT REQUEST FOR PMI SGL: Please pay DIPROTEC XOF 147 500 for purchase softener salt",
      name: "Fanta Guerineau",
      phone: "221776443634",
      email: "fanta.guerineau@alphamead.com",
      startDate: "20/09/2024",
      startTime: "02:25 PM",
      imprest: "No",
      fee: "No",
      approve: "Yes",
      po: "No",
      status: "Open"
    },

    4:{
      number: "0033933",
      createdDate: "20/09/2024",
      workNumber: "#0005700",
      type: "Unplanned",
      facility: "PMI SENEGAL",
      category: "Payment Request",
      subcategory: "Payment Request",
      priority: "Normal",
      title: "Payment Request",
      description: "PAYMENT REQUEST FOR PMI SGL: Please pay DIPROTEC XOF 147 500 for purchase softener salt",
      name: "Fanta Guerineau",
      phone: "221776443634",
      email: "fanta.guerineau@alphamead.com",
      startDate: "20/09/2024",
      startTime: "02:25 PM",
      imprest: "No",
      fee: "No",
      approve: "Yes",
      po: "No",
      status: "Open"
    },

    5:{
      number: "0033933",
      createdDate: "20/09/2024",
      workNumber: "#0005700",
      type: "Unplanned",
      facility: "PMI SENEGAL",
      category: "Payment Request",
      subcategory: "Payment Request",
      priority: "Normal",
      title: "Payment Request",
      description: "PAYMENT REQUEST FOR PMI SGL: Please pay DIPROTEC XOF 147 500 for purchase softener salt",
      name: "Fanta Guerineau",
      phone: "221776443634",
      email: "fanta.guerineau@alphamead.com",
      startDate: "20/09/2024",
      startTime: "02:25 PM",
      imprest: "No",
      fee: "No",
      approve: "Yes",
      po: "No",
      status: "Open"
    },

    6:{
      number: "0033933",
      createdDate: "20/09/2024",
      workNumber: "#0005700",
      type: "Unplanned",
      facility: "PMI SENEGAL",
      category: "Payment Request",
      subcategory: "Payment Request",
      priority: "Normal",
      title: "Payment Request",
      description: "PAYMENT REQUEST FOR PMI SGL: Please pay DIPROTEC XOF 147 500 for purchase softener salt",
      name: "Fanta Guerineau",
      phone: "221776443634",
      email: "fanta.guerineau@alphamead.com",
      startDate: "20/09/2024",
      startTime: "02:25 PM",
      imprest: "No",
      fee: "No",
      approve: "Yes",
      po: "No",
      status: "Open"
    },

    7:{
      number: "0033933",
      createdDate: "20/09/2024",
      workNumber: "#0005700",
      type: "Unplanned",
      facility: "PMI SENEGAL",
      category: "Payment Request",
      subcategory: "Payment Request",
      priority: "Normal",
      title: "Payment Request",
      description: "PAYMENT REQUEST FOR PMI SGL: Please pay DIPROTEC XOF 147 500 for purchase softener salt",
      name: "Fanta Guerineau",
      phone: "221776443634",
      email: "fanta.guerineau@alphamead.com",
      startDate: "20/09/2024",
      startTime: "02:25 PM",
      imprest: "No",
      fee: "No",
      approve: "Yes",
      po: "No",
      status: "Open"
    },

    8:{
      number: "0033933",
      createdDate: "20/09/2024",
      workNumber: "#0005700",
      type: "Unplanned",
      facility: "PMI SENEGAL",
      category: "Payment Request",
      subcategory: "Payment Request",
      priority: "Normal",
      title: "Payment Request",
      description: "PAYMENT REQUEST FOR PMI SGL: Please pay DIPROTEC XOF 147 500 for purchase softener salt",
      name: "Fanta Guerineau",
      phone: "221776443634",
      email: "fanta.guerineau@alphamead.com",
      startDate: "20/09/2024",
      startTime: "02:25 PM",
      imprest: "No",
      fee: "No",
      approve: "Yes",
      po: "No",
      status: "Open"
    },

    9:{
      number: "0033933",
      createdDate: "20/09/2024",
      workNumber: "#0005700",
      type: "Unplanned",
      facility: "PMI SENEGAL",
      category: "Payment Request",
      subcategory: "Payment Request",
      priority: "Normal",
      title: "Payment Request",
      description: "PAYMENT REQUEST FOR PMI SGL: Please pay DIPROTEC XOF 147 500 for purchase softener salt",
      name: "Fanta Guerineau",
      phone: "221776443634",
      email: "fanta.guerineau@alphamead.com",
      startDate: "20/09/2024",
      startTime: "02:25 PM",
      imprest: "No",
      fee: "No",
      approve: "Yes",
      po: "No",
      status: "Open"
    },

    10:{
      number: "0033933",
      createdDate: "20/09/2024",
      workNumber: "#0005700",
      type: "Unplanned",
      facility: "PMI SENEGAL",
      category: "Payment Request",
      subcategory: "Payment Request",
      priority: "Normal",
      title: "Payment Request",
      description: "PAYMENT REQUEST FOR PMI SGL: Please pay DIPROTEC XOF 147 500 for purchase softener salt",
      name: "Fanta Guerineau",
      phone: "221776443634",
      email: "fanta.guerineau@alphamead.com",
      startDate: "20/09/2024",
      startTime: "02:25 PM",
      imprest: "No",
      fee: "No",
      approve: "Yes",
      po: "No",
      status: "Open"
    },

  11:{
      number: "0033933",
      createdDate: "20/09/2024",
      workNumber: "#0005700",
      type: "Unplanned",
      facility: "PMI SENEGAL",
      category: "Payment Request",
      subcategory: "Payment Request",
      priority: "Normal",
      title: "Payment Request",
      description: "PAYMENT REQUEST FOR PMI SGL: Please pay DIPROTEC XOF 147 500 for purchase softener salt",
      name: "Fanta Guerineau",
      phone: "221776443634",
      email: "fanta.guerineau@alphamead.com",
      startDate: "20/09/2024",
      startTime: "02:25 PM",
      imprest: "No",
      fee: "No",
      approve: "Yes",
      po: "No",
      status: "Open"
    },

    
  };


  const displayItemDetails = (details) => {
    document.getElementById('number').innerText = details.number
    document.getElementById('created-date').innerText = details.createdDate;
    document.getElementById('work-no').innerText = details.workNumber;
    document.getElementById('type').innerText = details.type;
    document.getElementById('facility').innerText = details.facility;
    document.getElementById('category').innerText = details.category;
    document.getElementById('sub-category').innerText = details.subcategory;
    document.getElementById('priority').innerText = details.priority;
    document.getElementById('title').innerText = details.title;
    document.getElementById('description').innerText = details.description;
    document.getElementById('names').innerText = details.name;
    document.getElementById('phone').innerText = details.phone;
    document.getElementById('email').innerText = details.email;
    document.getElementById('start-date').innerText = details.startDate;
    document.getElementById('start-time').innerText = details.startTime;
    document.getElementById('imprest').innerText = details.imprest;
    document.getElementById('mob-fee').innerText = details.fee;
    document.getElementById('approve').innerText = details.approve;
    document.getElementById('p-o').innerText = details.po;
    document.getElementById('status').innerText = details.status;
  }
  
  sidebarContent.addEventListener('click', (event) => {
    const clickedItem = event.target.closest('.workOrder-sidebar_content');
    if (clickedItem) {
      const itemId = clickedItem.dataset.id;
      const details = workOrderDetails[itemId];
      if (details) {
        defaultImage.style.display = 'none';
        workOrderContent.style.display = 'block';
        displayItemDetails(details);
      }
    }
  });

  // Sample data to mimic multiple work order items
const workOrders = [
  { id: 1, name: '0033933', description: 'Payment Request', status: 'Open' },
  { id: 2, name: '0033932', description: 'Payment Request', status: 'Open' },
  { id: 3, name: '0033931', description: 'Payment Request', status: 'Open' },
  { id: 4, name: '0033930', description: 'Waste management', status: 'New' },
  { id: 5, name: '0033929', description: 'Security Services', status: 'New' },
  { id: 6, name: '0033928', description: 'Maintenance', status: 'Pending' },
  { id: 7, name: '0033927', description: 'IT Support', status: 'Completed' },
  { id: 8, name: '0033926', description: 'Cleaning Services', status: 'In Progress' },
  { id: 9, name: '0033925', description: 'Security Services', status: 'New' },
  { id: 10, name: '0033924', description: 'Network Installation', status: 'Completed' },
  { id: 11, name: '0033923', description: 'Plumbing Work', status: 'In Progress' },
  { id: 12, name: '0033922', description: 'Electrical Work', status: 'Open' }
];

// Number of work orders to show initially
let workOrdersToShow = 10;




// Function to render work orders
function renderWorkOrders() {
  // Clear current contents
  sidebarContent.innerHTML = '';
  

  // Render the number of work orders specified by workOrdersToShow
  workOrders.slice(0, workOrdersToShow).forEach(order => {
    const content = `
      <div class="workOrder-sidebar_content" data-id="${order.id}">
        <div class="workOrder-name">
          <span>${order.name}</span>
          <h6>${order.description}</h6>
        </div>
        <div class="workOrder-status">
          <h6>${order.description}</h6>
          <h6>${order.status}</h6>
        </div>
      </div>
    `;
    sidebarContent.insertAdjacentHTML('beforeend', content);
  });
  workOrderCount.textContent = `Showing 1 - ${workOrdersToShow} of ${workOrders.length}`;

  sidebarContent.scrollTop = sidebarContent.scrollHeight - previousScrollHeight;
}

// Event listener for the "Load More" button
loadMoreBtn.addEventListener('click', () => {
  // Increase the number of work orders to show by 5
  workOrdersToShow += 5;

  // If the number of work orders to show exceeds the total, hide the button
  if (workOrdersToShow >= workOrders.length) {
    workOrdersToShow = workOrders.length;
    // loadMoreBtn.style.display = 'none';
  }

  // Render the updated work orders
  renderWorkOrders();
});

// Initial render
renderWorkOrders();

})
} catch (error) {
  console.log(error)
}

// Javascript Logic for Payment Requisition
try {
  //Toggle Subcategory Sidebar

document.addEventListener('DOMContentLoaded', () => {
  const sidebarContent = document.querySelector('.payment-sidebar_contents');
  const paymentContent = document.querySelector('.');
  const defaultImage = document.getElementById('default-image')
  const loadMoreBtn = document.getElementById('loadMoreBtn');
  const paymentCount = document.getElementById('paymentCount');

  let paymentSidebar = document.querySelector(".payment-sidebar");
  let paymentSidebarBtn = document.querySelector(".payment-sidebarBtn");

  paymentSidebarBtn.addEventListener('click', () => {
    paymentSidebar.classList.toggle('active');
  })




  const paymentDetails = {
    1:{
      nuumber: "0007837",
      createdDate: "23/09/2024",
      reqDate: "23/09/2024",
      pay: "Makind Ajayi (Personnel)",
      paymentDate: "25/09/2024",
      retire: "No",
      approve: "No",
      remark: "Urgently required",
      status: "New",
    },

    2:{
      nuumber: "0007837",
      createdDate: "23/09/2024",
      reqDate: "23/09/2024",
      pay: "Makind Ajayi (Personnel)",
      paymentDate: "25/09/2024",
      retire: "No",
      approve: "No",
      remark: "Urgently required",
      status: "New",
    },

    3:{
      nuumber: "0007837",
      createdDate: "23/09/2024",
      reqDate: "23/09/2024",
      pay: "Makind Ajayi (Personnel)",
      paymentDate: "25/09/2024",
      retire: "No",
      approve: "No",
      remark: "Urgently required",
      status: "New",
    },

    4:{
      nuumber: "0007837",
      createdDate: "23/09/2024",
      reqDate: "23/09/2024",
      pay: "Makind Ajayi (Personnel)",
      paymentDate: "25/09/2024",
      retire: "No",
      approve: "No",
      remark: "Urgently required",
      status: "New",
    },

    5:{
      nuumber: "0007837",
      createdDate: "23/09/2024",
      reqDate: "23/09/2024",
      pay: "Makind Ajayi (Personnel)",
      paymentDate: "25/09/2024",
      retire: "No",
      approve: "No",
      remark: "Urgently required",
      status: "New",
    },

    6:{
      nuumber: "0007837",
      createdDate: "23/09/2024",
      reqDate: "23/09/2024",
      pay: "Makind Ajayi (Personnel)",
      paymentDate: "25/09/2024",
      retire: "No",
      approve: "No",
      remark: "Urgently required",
      status: "New",
    },

    7:{
      nuumber: "0007837",
      createdDate: "23/09/2024",
      reqDate: "23/09/2024",
      pay: "Makind Ajayi (Personnel)",
      paymentDate: "25/09/2024",
      retire: "No",
      approve: "No",
      remark: "Urgently required",
      status: "New",
    },

    8:{
      nuumber: "0007837",
      createdDate: "23/09/2024",
      reqDate: "23/09/2024",
      pay: "Makind Ajayi (Personnel)",
      paymentDate: "25/09/2024",
      retire: "No",
      approve: "No",
      remark: "Urgently required",
      status: "New",
    },

    9:{
      nuumber: "0007837",
      createdDate: "23/09/2024",
      reqDate: "23/09/2024",
      pay: "Makind Ajayi (Personnel)",
      paymentDate: "25/09/2024",
      retire: "No",
      approve: "No",
      remark: "Urgently required",
      status: "New",
    },

    10:{
      nuumber: "0007837",
      createdDate: "23/09/2024",
      reqDate: "23/09/2024",
      pay: "Makind Ajayi (Personnel)",
      paymentDate: "25/09/2024",
      retire: "No",
      approve: "No",
      remark: "Urgently required",
      status: "New",
    },
    
  };


  const displayItemDetails = (details) => {
    document.getElementById('num').innerText = details.nuumber;
    document.getElementById('created-date').innerText = details.createdDate;
    document.getElementById('req-date').innerText = details.reqDate;
    document.getElementById('pay').innerText = details.pay;
    document.getElementById('payment-date').innerText = details.paymentDate;
    document.getElementById('retirement').innerText = details.retire;
    document.getElementById('remark').innerText = details.remark;
    document.getElementById('approval').innerText = details.approve;
    document.getElementById('status').innerText = details.status;
  }
  
  sidebarContent.addEventListener('click', (event) => {
    const clickedItem = event.target.closest('.payment-sidebar_content');
    if (clickedItem) {
      const itemId = clickedItem.dataset.id;
      const details = paymentDetails[itemId];
      if (details) {
        defaultImage.style.display = 'none';
        paymentContent.style.display = 'block';
        displayItemDetails(details);
      }
    }
  });

  // Sample data to mimic multiple work order items
const payments = [
  { id: 1, name: 'A/C MAINTENANCE', duration: '3 Months', description: 'Hvac system', status: 'Active' },
  { id: 2, name: 'CCTV AND FIRE ALARM', duration: '3 Months', description: 'Extra low voltage', status: 'Active' },
  { id: 3, name: 'CHILLER MAINTENANCE', duration: '3 Months', description: 'Hvac (heating / cooling)', status: 'Active' },
  { id: 4, name: 'CLEANING INTERNAL DRAINAGE', duration: '1 Month', description: 'Civil works & Construction', status: 'Active' },
  { id: 5, name: 'Dstv, Pabx and LAN System (Daily)', duration: '3 Months', description: 'Dstv', status: 'Inactive' },
  { id: 6, name: 'Dstv, Pabx and LAN System (Daily)', duration: '1 day', description: 'Dstv', status: 'Inactive' },
  { id: 7, name: 'Dstv, Pabx and LAN System (Daily)', duration: '3 Months', description: 'Dstv', status: 'Inactive' },
  { id: 8, name: 'Dstv, Pabx and LAN System (Daily)', duration: '3 Months', description: 'Dstv', status: 'Inactive' },
  { id: 9, name: 'Dstv, Pabx and LAN System (Daily)', duration: '3 Months', description: 'Dstv', status: 'Inactive' },
  { id: 10, name: 'Dstv, Pabx and LAN System (Daily)', duration: '3 Months', description: 'Dstv', status: 'Inactive' },
  { id: 11, name: 'Dstv, Pabx and LAN System (Daily)', duration: '3 Months', description: 'Dstv', status: 'Inactive' },
  { id: 12, name: 'Dstv, Pabx and LAN System (Daily)', duration: '3 Months', description: 'Dstv', status: 'Inactive' },
];

// Number of work orders to show initially
let paymentToShow = 10;




// Function to render work orders
function renderPayments() {
  // Clear current contents
  sidebarContent.innerHTML = '';
  

  // Render the number of work orders specified by workOrdersToShow
  payments.slice(0, paymentToShow).forEach(order => {
    const content = `
      <div class="payment-sidebar_content" data-id="${order.id}">
        <div class="payment-name">
          <span>${order.name}</span>
          <h6>${order.duration}</h6>
        </div>
        <div class="payment-status">
          <h6>${order.description}</h6>
          <h6>${order.status}</h6>
        </div>
      </div>
    `;
    sidebarContent.insertAdjacentHTML('beforeend', content);
  });
  paymentCount.textContent = `Showing 1 - ${paymentToShow} of ${payments.length}`;

  
}

// Event listener for the "Load More" button
loadMoreBtn.addEventListener('click', () => {
  // Increase the number of work orders to show by 5
  paymentToShow += 5;

  // If the number of work orders to show exceeds the total, hide the button
  if (paymentToShow >= payments.length) {
    paymentToShow = payments.length;
    // loadMoreBtn.style.display = 'none';
  }

  // Render the updated work orders
  renderPayments();
});

// Initial render
renderPayments();

})
} catch (error) {
  console.log(error)
}

// Javascript Logic for PPM Setting
try {
  //Toggle Subcategory Sidebar

document.addEventListener('DOMContentLoaded', () => {
  const sidebarContent = document.querySelector('.ppmSetting-sidebar_contents');
  const ppmSettingContent = document.querySelector('.ppmSetting-body_content');
  const defaultImage = document.getElementById('default-image')
  const loadMoreBtn = document.getElementById('loadMoreBtn');
  const ppmSettingCount = document.getElementById('ppmSettingCount');

  let ppmSettingSidebar = document.querySelector(".ppmSetting-sidebar");
  let ppmSettingSidebarBtn = document.querySelector(".ppmSetting-sidebarBtn");

  ppmSettingSidebarBtn.addEventListener('click', () => {
    ppmSettingSidebar.classList.toggle('active');
  })




  const ppmSettingDetails = {
    1:{
      description: "A.C Maintenance",
      category: "Hvac System",
      frequency: "3 Months",
      currency: "NGN",
      notify: "1 Month",
      reminder: "1 Month",
      status: "Open"
    },

    2:{
      description: "A.C Maintenance",
      category: "Hvac System",
      frequency: "3 Months",
      currency: "NGN",
      notify: "1 Month",
      reminder: "1 Month",
      status: "Open"
    },

    3:{
      description: "A.C Maintenance",
      category: "Hvac System",
      frequency: "3 Months",
      currency: "NGN",
      notify: "1 Month",
      reminder: "1 Month",
      status: "Open"
    },

    4:{
      description: "A.C Maintenance",
      category: "Hvac System",
      frequency: "3 Months",
      currency: "NGN",
      notify: "1 Month",
      reminder: "1 Month",
      status: "Open"
    },

    5:{
      description: "A.C Maintenance",
      category: "Hvac System",
      frequency: "3 Months",
      currency: "NGN",
      notify: "1 Month",
      reminder: "1 Month",
      status: "Open"
    },

    6:{
      description: "A.C Maintenance",
      category: "Hvac System",
      frequency: "3 Months",
      currency: "NGN",
      notify: "1 Month",
      reminder: "1 Month",
      status: "Open"
    },

    7:{
      description: "A.C Maintenance",
      category: "Hvac System",
      frequency: "3 Months",
      currency: "NGN",
      notify: "1 Month",
      reminder: "1 Month",
      status: "Open"
    },

    8:{
      description: "A.C Maintenance",
      category: "Hvac System",
      frequency: "3 Months",
      currency: "NGN",
      notify: "1 Month",
      reminder: "1 Month",
      status: "Open"
    },

    9:{
      description: "A.C Maintenance",
      category: "Hvac System",
      frequency: "3 Months",
      currency: "NGN",
      notify: "1 Month",
      reminder: "1 Month",
      status: "Open"
    },

    10:{
      description: "A.C Maintenance",
      category: "Hvac System",
      frequency: "3 Months",
      currency: "NGN",
      notify: "1 Month",
      reminder: "1 Month",
      status: "Open"
    },

   

    
  };


  const displayItemDetails = (details) => {
    document.getElementById('description').innerText = details.description
    document.getElementById('category').innerText = details.category;
    document.getElementById('frequency').innerText = details.frequency;
    document.getElementById('currency').innerText = details.currency;
    document.getElementById('notify').innerText = details.notify;
    document.getElementById('remainder').innerText = details.reminder;
    document.getElementById('status').innerText = details.status;
  }
  
  sidebarContent.addEventListener('click', (event) => {
    const clickedItem = event.target.closest('.ppmSetting-sidebar_content');
    if (clickedItem) {
      const itemId = clickedItem.dataset.id;
      const details = ppmSettingDetails[itemId];
      if (details) {
        defaultImage.style.display = 'none';
        ppmSettingContent.style.display = 'block';
        displayItemDetails(details);
      }
    }
  });

  // Sample data to mimic multiple work order items
const ppmSettings = [
  { id: 1, name: 'A/C MAINTENANCE', duration: '3 Months', description: 'Hvac system', status: 'Active' },
  { id: 2, name: 'CCTV AND FIRE ALARM', duration: '3 Months', description: 'Extra low voltage', status: 'Active' },
  { id: 3, name: 'CHILLER MAINTENANCE', duration: '3 Months', description: 'Hvac (heating / cooling)', status: 'Active' },
  { id: 4, name: 'CLEANING INTERNAL DRAINAGE', duration: '1 Month', description: 'Civil works & Construction', status: 'Active' },
  { id: 5, name: 'Dstv, Pabx and LAN System (Daily)', duration: '3 Months', description: 'Dstv', status: 'Inactive' },
  { id: 6, name: 'Dstv, Pabx and LAN System (Daily)', duration: '1 day', description: 'Dstv', status: 'Inactive' },
  { id: 7, name: 'Dstv, Pabx and LAN System (Daily)', duration: '3 Months', description: 'Dstv', status: 'Inactive' },
  { id: 8, name: 'Dstv, Pabx and LAN System (Daily)', duration: '3 Months', description: 'Dstv', status: 'Inactive' },
  { id: 9, name: 'Dstv, Pabx and LAN System (Daily)', duration: '3 Months', description: 'Dstv', status: 'Inactive' },
  { id: 10, name: 'Dstv, Pabx and LAN System (Daily)', duration: '3 Months', description: 'Dstv', status: 'Inactive' },
  { id: 11, name: 'Dstv, Pabx and LAN System (Daily)', duration: '3 Months', description: 'Dstv', status: 'Inactive' },
  { id: 12, name: 'Dstv, Pabx and LAN System (Daily)', duration: '3 Months', description: 'Dstv', status: 'Inactive' },
];

// Number of work orders to show initially
let ppmSettingToShow = 10;




// Function to render work orders
function renderPpmSettings() {
  // Clear current contents
  sidebarContent.innerHTML = '';
  

  // Render the number of work orders specified by workOrdersToShow
  ppmSettings.slice(0, ppmSettingToShow).forEach(order => {
    const content = `
      <div class="ppmSetting-sidebar_content" data-id="${order.id}">
        <div class="ppmSetting-name">
          <span>${order.name}</span>
          <h6>${order.duration}</h6>
        </div>
        <div class="ppmSetting-status">
          <h6>${order.description}</h6>
          <h6>${order.status}</h6>
        </div>
      </div>
    `;
    sidebarContent.insertAdjacentHTML('beforeend', content);
  });
  ppmSettingCount.textContent = `Showing 1 - ${ppmSettingToShow} of ${ppmSettings.length}`;

  
}

// Event listener for the "Load More" button
loadMoreBtn.addEventListener('click', () => {
  // Increase the number of work orders to show by 5
  ppmSettingToShow += 5;

  // If the number of work orders to show exceeds the total, hide the button
  if (ppmSettingToShow >= ppmSettings.length) {
    ppmSettingToShow = ppmSettings.length;
    // loadMoreBtn.style.display = 'none';
  }

  // Render the updated work orders
  renderPpmSettings();
});

// Initial render
renderPpmSettings();

})
} catch (error) {
  console.log(error)
}

// Javascript Logic for Asset Register and Inventory Register

// Displaying Table Content and dynamically control the length of the table based on the select input

try {
  const tableBody = document.getElementById('tableBody');
  const rowCountSelect = document.getElementById('rows')
  const secondModalContent = document.querySelector('.second-modal_body');
  const secondModal = document.querySelector('.second');
  const tableData = [
  {
    id: 1,
    items: '0000028',
    category: 'Plant and Machineries',
    subCategory: "Living Room",
    model: "10HP LIFT PUMP",
    partNumber: "",
    assetTag: "28",
    serialNumber: "NA",
    quantity: "2",
    unitPrice: "0",
    amount: "0",
    reorderLevel: "",
    minimum: "",
    maximum: "",
    location: "1004 Project (Cluster C) <br> 1004 (Cluster C)",
    flag: "",
    status: "In Use <br> NA"
  },
  {
    id: 2,
    items: '0000028',
    category: 'appliances',
    subCategory: "Living Room",
    model: "10HP LIFT PUMP",
    partNumber: "",
    assetTag: "28",
    serialNumber: "NA",
    quantity: "2",
    unitPrice: "0",
    amount: "0",
    reorderLevel: "",
    minimum: "",
    maximum: "",
    location: "1004 Project (Cluster C) <br> 1004 (Cluster C)",
    flag: "",
    status: "In Use <br> NA"
  },
  {
    id: 3,
    items: '0000028',
    category: 'Plant and Machineries',
    subCategory: "Living Room",
    model: "10HP LIFT PUMP",
    partNumber: "",
    assetTag: "28",
    serialNumber: "NA",
    quantity: "2",
    unitPrice: "0",
    amount: "0",
    reorderLevel: "",
    minimum: "",
    maximum: "",
    location: "1004 Project (Cluster C) <br> 1004 (Cluster C)",
    flag: "",
    status: "In Use <br> NA"
  },
  {
    id: 4,
    items: '0000028',
    category: 'Plant and Machineries',
    subCategory: "Living Room",
    model: "10HP LIFT PUMP",
    partNumber: "",
    assetTag: "28",
    serialNumber: "NA",
    quantity: "2",
    unitPrice: "0",
    amount: "0",
    reorderLevel: "",
    minimum: "",
    maximum: "",
    location: "1004 Project (Cluster C) <br> 1004 (Cluster C)",
    flag: "",
    status: "In Use <br> NA"
  },
  {
    id: 5,
    items: '0000028',
    category: 'Plant and Machineries',
    subCategory: "Living Room",
    model: "10HP LIFT PUMP",
    partNumber: "",
    assetTag: "28",
    serialNumber: "NA",
    quantity: "2",
    unitPrice: "0",
    amount: "0",
    reorderLevel: "",
    minimum: "",
    maximum: "",
    location: "1004 Project (Cluster C) <br> 1004 (Cluster C)",
    flag: "",
    status: "In Use <br> NA"
  },
  {
    id: 6,
    items: '0000028',
    category: 'Plant and Machineries',
    subCategory: "Living Room",
    model: "10HP LIFT PUMP",
    partNumber: "",
    assetTag: "28",
    serialNumber: "NA",
    quantity: "2",
    unitPrice: "0",
    amount: "0",
    reorderLevel: "",
    minimum: "",
    maximum: "",
    location: "1004 Project (Cluster C) <br> 1004 (Cluster C)",
    flag: "",
    status: "In Use <br> NA"
  },
  {
    id: 7,
    items: '0000028',
    category: 'Plant and Machineries',
    subCategory: "Living Room",
    model: "10HP LIFT PUMP",
    partNumber: "",
    assetTag: "28",
    serialNumber: "NA",
    quantity: "2",
    unitPrice: "0",
    amount: "0",
    reorderLevel: "",
    minimum: "",
    maximum: "",
    location: "1004 Project (Cluster C) <br> 1004 (Cluster C)",
    flag: "",
    status: "In Use <br> NA"
  },
  {
    id: 8,
    items: '0000028',
    category: 'Plant and Machineries',
    subCategory: "Living Room",
    model: "10HP LIFT PUMP",
    partNumber: "",
    assetTag: "28",
    serialNumber: "NA",
    quantity: "2",
    unitPrice: "0",
    amount: "0",
    reorderLevel: "",
    minimum: "",
    maximum: "",
    location: "1004 Project (Cluster C) <br> 1004 (Cluster C)",
    flag: "",
    status: "In Use <br> NA"
  },
  {
    id: 9,
    items: '0000028',
    category: 'Plant and Machineries',
    subCategory: "Living Room",
    model: "10HP LIFT PUMP",
    partNumber: "",
    assetTag: "28",
    serialNumber: "NA",
    quantity: "2",
    unitPrice: "0",
    amount: "0",
    reorderLevel: "",
    minimum: "",
    maximum: "",
    location: "1004 Project (Cluster C) <br> 1004 (Cluster C)",
    flag: "",
    status: "In Use <br> NA"
  },
  {
    id: 10,
    items: '0000028',
    category: 'Plant and Machineries',
    subCategory: "Living Room",
    model: "10HP LIFT PUMP",
    partNumber: "",
    assetTag: "28",
    serialNumber: "NA",
    quantity: "2",
    unitPrice: "0",
    amount: "0",
    reorderLevel: "",
    minimum: "",
    maximum: "",
    location: "1004 Project (Cluster C) <br> 1004 (Cluster C)",
    flag: "",
    status: "In Use <br> NA"
  },

  ];

  function populateTable() {
  tableData.forEach(item => {
    const row = document.createElement('tr');

    const col1 = document.createElement('td');
    col1.innerHTML = item.items;
    col1.classList.add('table-row')
    row.appendChild(col1);

    const col2 = document.createElement('td');
    col2.innerHTML = item.category;
    col2.classList.add('table-row')
    row.appendChild(col2);

    const col3 = document.createElement('td');
    col3.innerHTML = item.subCategory;
    col3.classList.add('table-row')
    row.appendChild(col3);

    const col4 = document.createElement('td');
    col4.innerHTML = item.model;
    col4.classList.add('table-row')
    row.appendChild(col4);

    const col5 = document.createElement('td');
    col5.innerHTML = item.partNumber;
    col5.classList.add('table-row')
    row.appendChild(col5);

    const col6 = document.createElement('td');
    col6.innerHTML = item.assetTag;
    col6.classList.add('table-row')
    row.appendChild(col6);

    const col7 = document.createElement('td');
    col7.innerHTML = item.serialNumber;
    col7.classList.add('table-row')
    row.appendChild(col7);

    const col8 = document.createElement('td');
    col8.innerHTML = item.quantity;
    col8.classList.add('table-row')
    row.appendChild(col8);

    const col9 = document.createElement('td');
    col9.innerHTML = item.unitPrice;
    col9.classList.add('table-row')
    row.appendChild(col9);

    const col10 = document.createElement('td');
    col10.innerHTML = item.amount;
    col10.classList.add('table-row')
    row.appendChild(col10);

    const col11 = document.createElement('td');
    col11.innerHTML = item.reorderLevel
    col11.classList.add('table-row')
    row.appendChild(col11);

    const col12 = document.createElement('td');
    col12.innerHTML = item.minimum;
    col12.classList.add('table-row')
    row.appendChild(col12);

    const col13 = document.createElement('td');
    col13.innerHTML = item.maximum;
    col13.classList.add('table-row')
    row.appendChild(col13);

    const col14 = document.createElement('td');
    col14.innerHTML = item.location;
    col14.classList.add('table-row')
    row.appendChild(col14);

    const col15 = document.createElement('td');
    col15.innerHTML = item.flag;
    col15.classList.add('table-row')
    row.appendChild(col15);

    const col16 = document.createElement('td');
    col16.innerHTML = item.status;
    col16.classList.add('table-row')
    row.appendChild(col16);

    tableBody.appendChild(row);
  })
  }

  function updateRows() {
  const rowCount = parseInt(rowCountSelect.value);
  const rows = tableBody.children;
  for (let i = 0; i < rows.length; i++) {
    if (i < rowCount) {
      rows[i].style.display = ''; // Show the row
    } else {
      rows[i].style.display = 'none'; // Hide the row
    }
  }
  }

  rowCountSelect.addEventListener('change', updateRows);

  populateTable();

  //Logic for the spinner and the modal
  const loadButton = document.getElementById('load-button');
  const loader = document.getElementById('loader');
  const myModal = new bootstrap.Modal(document.getElementById('ExtralargeModal'));

  loadButton.addEventListener('click', () => {

  loader.style.display = 'block';

  setTimeout(() => {
    loader.style.display = 'none';
    myModal.show();
  }, 3000);
  });

  //Logic for search functionality

  function searchTable() {
  const searchQuery = document.getElementById('searchInput').value.toLowerCase();

  const rows = tableBody.children;

  for (let i = 0; i < rows.length; i++) {
    const rowData = rows[i].innerText.toLowerCase();
    if (rowData.includes(searchQuery)) {
      rows[i].style.display = ''; // Show the row if it matches the search query
    } else {
      rows[i].style.display = 'none'; // Hide the row if it doesn't match
    }
  }
  }

  //Logic for the minimize and maximize functionality for both modals

  function showIcons() {
  const fullscreenIcon = document.querySelector('.fullscreen');
  const minimizedIcon = document.querySelector('.minimized');
  const arrowIcon = document.querySelector('.arrow');
  fullscreenIcon.style.display = 'inline-block';
  minimizedIcon.style.display = 'inline-block';
  arrowIcon.style.display = 'none'
  }

  function hideIcons() {
  const fullscreenIcon = document.querySelector('.fullscreen');
  const minimizedIcon = document.querySelector('.minimized');
  const arrowIcon = document.querySelector('.arrow');
  fullscreenIcon.style.display = 'none';
  minimizedIcon.style.display = 'none';
  arrowIcon.style.display = 'inline-block'
  }


function toggleModalSize() {
const modalDialog = document.querySelector('.modal-dialog');

if (modalDialog.classList.contains('modal-xl')) {
  // Maximizing to fullscreen
  modalDialog.classList.remove('modal-xl');
  modalDialog.classList.add('modal-fullscreen');
} else {
  // Minimizing back to default size
  modalDialog.classList.remove('modal-fullscreen');
  modalDialog.classList.add('modal-xl');
}
}

function toggleMiniSize() {
const modalDialog = document.querySelector('.modal-dialog');

if (modalDialog.classList.contains('modal-xl')) {
    // Maximizing to fullscreen
    modalDialog.classList.remove('modal-xl');
    modalDialog.classList.add('modal-lg');
} else {
    // Minimizing back to default size
    modalDialog.classList.remove('modal-lg');
    modalDialog.classList.add('modal-xl');
}
}



//Modal for each row
tableBody.querySelectorAll('tr').forEach(row => {
row.setAttribute('data-bs-toggle', 'modal')
row.setAttribute('data-bs-target', '#rowDetailsModal')
row.addEventListener('click', () => {
  const data = Array.from(row.children).map(cell => cell.innerHTML)
  const modal = document.getElementById('rowDetailsModal');
  modal.querySelector('#name').innerHTML = '#' + data[0]
  modal.querySelector('#category').innerHTML = data[1]
  modal.querySelector('#subcategory').innerHTML = data[2]
  modal.querySelector('#model').innerHTML = data[3]
  modal.querySelector('#serial').innerHTML = data[4]
  modal.querySelector('#asset').innerHTML = data[5]
  modal.querySelector('#log').innerHTML = data[6]
  modal.querySelector('#quantity').innerHTML = data[7]
  modal.querySelector('#unit-price').innerHTML = data[8]
  modal.querySelector('#location').innerHTML = data[13]
  modal.querySelector('#status').innerHTML = data[15]
  modal.style.display = 'block';
})
})


const rowDetailsModal = document.getElementById('rowDetailsModal');

loadButton.addEventListener('click', () => {

loader.style.display = 'block';

setTimeout(() => {
  loader.style.display = 'none';
  rowDetailsModal.show();
}, 3000);
});

} catch (error) {
  console.log('Second code', error)
}


// Javascript Logic for Item Register

try {
  // Toggle Item Sidebar
  let itemSidebar = document.querySelector(".itemRequest-sidebar");
  let itemsidebarBtn = document.querySelector(".itemRequest-sidebarBtn");

  itemsidebarBtn.addEventListener('click', () => {
    itemSidebar.classList.toggle('active');
  })

document.addEventListener('DOMContentLoaded', () => {
  const items = document.querySelectorAll('.itemRequest-sidebar_content');
  const defaultImage = document.getElementById('default-image');
  const itemsContent = document.querySelector('.itemRequest-body_content');



  const detailsMap = {
      1:{
          number: '0000006',
          type: 'Use',
          category: 'Category 1',
          date: new Date(),
          department: 'Central Operations',
          status: 'Submitted',
          location: 'New Head Office'
      },
  
      2:{
          number: '0000005',
          type: 'Use',
          category: 'Category 2',
          date: new Date(),
          department: 'Central Operations',
          status: 'Submitted',
          location: 'New Head Office'
      }
  };

  const options = { day: '2-digit', month: '2-digit', year: 'numeric' };
  
  for (const id in detailsMap) {
      const detail = detailsMap[id];
      const formattedDate = detail.date.toLocaleDateString('en-GB', options)
      detail.formattedDate = formattedDate;
  }
  const displayItemDetails = (details) => {
      document.getElementById('number').innerText = details.number
      document.getElementById('type').innerText = details.type;
      document.getElementById('date').innerText = details.formattedDate;
      document.getElementById('required-date').innerText = details.formattedDate;
      document.getElementById('item-department').innerText = details.department;
      document.getElementById('item-status').innerText = details.status;
      document.getElementById('location').innerText = details.location;
      // document.querySelectorAll('.item-date').innerText = details.formattedDate;
  }
  
  items.forEach(item => {
    item.addEventListener('click', () => {
      const itemId = item.dataset.id;
      const details = detailsMap[itemId];

      if (details) {
        defaultImage.style.display = 'none';
        itemsContent.style.display = 'block';
        displayItemDetails(details)
      }
    })
  });
})
} catch (error) {
  console.log('First code', error)
}

// Javascript Logic for Inventory Adjustment
try {
  let inventoryAdjustmentSidebar = document.querySelector(".inventoryAdjustment-sidebar");
  let inventoryAdjustmentSidebarBtn = document.querySelector(".inventoryAdjustment-sidebarBtn");

  inventoryAdjustmentSidebarBtn.addEventListener('click', () => {
    inventoryAdjustmentSidebar.classList.toggle('active');
  })
  document.addEventListener('DOMContentLoaded', () => {
    const inventoryAdjustments = document.querySelectorAll('.inventoryAdjustment-sidebar_content');
    const defaultImage = document.getElementById('default-image');
    const inventoryAdjustmentContent = document.querySelector('.inventoryAdjustment-body_content');



  const inventoryAdjustmentDetails = {
    1:{
      number: '0000006',
      type: 'Use',
      category: 'Category 1',
      date: new Date(),
      department: 'Central Operations',
      status: 'Submitted',
      location: 'New Head Office'
    },
  
    2:{
      number: '0000005',
      type: 'Use',
      category: 'Category 2',
      date: new Date(),
      department: 'Central Operations',
      status: 'Submitted',
      location: 'New Head Office'
    }
    };

    const options = { day: '2-digit', month: '2-digit', year: 'numeric' };
    
    for (const id in detailsMap) {
        const detail = detailsMap[id];
        const formattedDate = detail.date.toLocaleDateString('en-GB', options)
        detail.formattedDate = formattedDate;
    }
    const displayItemDetails = (details) => {
      document.getElementById('number').innerText = details.number
      document.getElementById('type').innerText = details.type;
      // document.getElementById('category').innerText = details.category;
      document.getElementById('date').innerText = details.formattedDate;
      document.getElementById('required-date').innerText = details.formattedDate;
      document.getElementById('item-department').innerText = details.department;
      document.getElementById('item-status').innerText = details.status;
      document.getElementById('location').innerText = details.location;
      // document.querySelectorAll('.item-date').innerText = details.formattedDate;
    }
    
    inventoryAdjustments.forEach(item => {
      item.addEventListener('click', () => {
        const itemId = item.dataset.id;
        const details = inventoryAdjustmentDetails[itemId];

        if (details) {
          defaultImage.style.display = 'none';
          inventoryAdjustmentContent.style.display = 'block';
          displayItemDetails(details)
        }
      })
    });
})
} catch (error) {
  console.log('Third code', error)
}

// Javascript Logic for Transfer Form

try {
  //Toggle Transfer Sidebar
let transferSidebar = document.querySelector(".transfer-sidebar");
let transferSidebarBtn = document.querySelector(".transfer-sidebarBtn");

transferSidebarBtn.addEventListener('click', () => {
    transferSidebar.classList.toggle('active');
})
document.addEventListener('DOMContentLoaded', () => {
  const transfers = document.querySelectorAll('.transfer-sidebar_content');
  const defaultImage = document.getElementById('default-image');
  const transferContent = document.querySelector('.t');



  const transferDetails = {
      1:{
          number: '0000006',
          type: 'Use',
          category: 'Category 1',
          date: new Date(),
          department: 'Central Operations',
          status: 'Submitted',
          location: 'New Head Office'
      },
  
      2:{
          number: '0000005',
          type: 'Use',
          category: 'Category 2',
          date: new Date(),
          department: 'Central Operations',
          status: 'Submitted',
          location: 'New Head Office'
      }
  };

  const options = { day: '2-digit', month: '2-digit', year: 'numeric' };
  
  for (const id in detailsMap) {
      const detail = detailsMap[id];
      const formattedDate = detail.date.toLocaleDateString('en-GB', options)
      detail.formattedDate = formattedDate;
  }
  const displayItemDetails = (details) => {
      document.getElementById('number').innerText = details.number
      document.getElementById('type').innerText = details.type;
      document.getElementById('category').innerText = details.category;
      document.getElementById('date').innerText = details.formattedDate;
      document.getElementById('required-date').innerText = details.formattedDate;
      document.getElementById('item-department').innerText = details.department;
      document.getElementById('item-status').innerText = details.status;
      document.getElementById('location').innerText = details.location;
      // document.querySelectorAll('.item-date').innerText = details.formattedDate;
  }
  
  transfers.forEach(item => {
      item.addEventListener('click', () => {
          const itemId = item.dataset.id;
          const details = transferDetails[itemId];
  
          if (details) {
              defaultImage.style.display = 'none';
              transferContent.style.display = 'block';
              displayItemDetails(details)
          }
      })
  });
})
} catch (error) {
  console.log(error)
}


// Javascript Logic for Movement History

try {
  //Displaying Table Content and dynamically control the length of the table based on the select input

const movementTableBody = document.getElementById('movement-tableBody');
const rowCountSelect = document.getElementById('rows')

const movementTableData = [
  {
    id: 1,
    items: '1',
    category: '17/03/2022',
    subCategory: "08:55 AM",
    model: "Oluwatomisin Isijola",
    partNumber: "0004090",
    assetTag: "N/A - CAMPHOR - Cleaning",
    serialNumber: "Deploy",
    quantity: "Alphamead Central Store",
    unitPrice: "Test Facility (002)",
    amount: "",
    reorderLevel: "1",
    minimum: "1",
    maximum: "",
    location: "",
    flag: "",
    status: ""
  },
  {
    id: 2,
    items: '2',
    category: '12/07/2021',
    subCategory: "05:06 PM",
    model: "SysServe Solutions",
    partNumber: "0005101",
    assetTag: "Air Conditioner 1 - Hvac",
    serialNumber: "Deploy",
    quantity: "",
    unitPrice: "New Head Office (AMF Operation)",
    amount: "",
    reorderLevel: "1",
    minimum: "1",
    maximum: "",
    location: "",
    flag: "",
    status: ""
  }
];

function populateTable() {
  movementTableData.forEach(item => {
    const row = document.createElement('tr');
  
    const col1 = document.createElement('td');
    col1.innerHTML = item.items;
    col1.classList.add('table-row')
    row.appendChild(col1);
  
    const col2 = document.createElement('td');
    col2.innerHTML = item.category;
    col2.classList.add('table-row')
    row.appendChild(col2);
  
    const col3 = document.createElement('td');
    col3.innerHTML = item.subCategory;
    col3.classList.add('table-row')
    row.appendChild(col3);
  
    const col4 = document.createElement('td');
    col4.innerHTML = item.model;
    col4.classList.add('table-row')
    row.appendChild(col4);
  
    const col5 = document.createElement('td');
    col5.innerHTML = item.partNumber;
    col5.classList.add('table-row')
    row.appendChild(col5);
  
    const col6 = document.createElement('td');
    col6.innerHTML = item.assetTag;
    col6.classList.add('table-row')
    row.appendChild(col6);
  
    const col7 = document.createElement('td');
    col7.innerHTML = item.serialNumber;
    col7.classList.add('table-row')
    row.appendChild(col7);
  
    const col8 = document.createElement('td');
    col8.innerHTML = item.quantity;
    col8.classList.add('table-row')
    row.appendChild(col8);
  
    const col9 = document.createElement('td');
    col9.innerHTML = item.unitPrice;
    col9.classList.add('table-row')
    row.appendChild(col9);
  
    const col10 = document.createElement('td');
    col10.innerHTML = item.amount;
    col10.classList.add('table-row')
    row.appendChild(col10);
  
    const col11 = document.createElement('td');
    col11.innerHTML = item.reorderLevel
    col11.classList.add('table-row')
    row.appendChild(col11);
  
    const col12 = document.createElement('td');
    col12.innerHTML = item.minimum;
    col12.classList.add('table-row')
    row.appendChild(col12);
  
    const col13 = document.createElement('td');
    col13.innerHTML = item.maximum;
    col13.classList.add('table-row')
    row.appendChild(col13);
  
    const col14 = document.createElement('td');
    col14.innerHTML = item.location;
    col14.classList.add('table-row')
    row.appendChild(col14);
  
    const col15 = document.createElement('td');
    col15.innerHTML = item.flag;
    col15.classList.add('table-row')
    row.appendChild(col15);
  
    const col16 = document.createElement('td');
    col16.innerHTML = item.status;
    col16.classList.add('table-row')
    row.appendChild(col16);
  
    movementTableBody.appendChild(row);
  })
}

function updateRows() {
  const rowCount = parseInt(rowCountSelect.value);
  const rows = movementTableBody.children;
  for (let i = 0; i < rows.length; i++) {
    if (i < rowCount) {
      rows[i].style.display = ''; // Show the row
    } else {
      rows[i].style.display = 'none'; // Hide the row
    }
  }
}

rowCountSelect.addEventListener('change', updateRows);

populateTable();

//Logic for the spinner and the modal
const loadButton = document.getElementById('load-button');
const loader = document.getElementById('loader');
const myModal = new bootstrap.Modal(document.getElementById('ExtralargeModal'));

loadButton.addEventListener('click', () => {

  loader.style.display = 'block';

  setTimeout(() => {
    loader.style.display = 'none';
    myModal.show();
  }, 3000);
});

//Logic for search functionality

function searchTable() {
  const searchQuery = document.getElementById('searchInput').value.toLowerCase();

  const rows = tableBody.children;

  for (let i = 0; i < rows.length; i++) {
    const rowData = rows[i].innerText.toLowerCase();
    if (rowData.includes(searchQuery)) {
      rows[i].style.display = ''; // Show the row if it matches the search query
    } else {
      rows[i].style.display = 'none'; // Hide the row if it doesn't match
    }
  }
}

//Logic for the minimize and maximize functionality for both modals

function showIcons() {
  const fullscreenIcon = document.querySelector('.fullscreen');
  const minimizedIcon = document.querySelector('.minimized');
  const arrowIcon = document.querySelector('.arrow');
  fullscreenIcon.style.display = 'inline-block';
  minimizedIcon.style.display = 'inline-block';
  arrowIcon.style.display = 'none'
}

function hideIcons() {
  const fullscreenIcon = document.querySelector('.fullscreen');
  const minimizedIcon = document.querySelector('.minimized');
  const arrowIcon = document.querySelector('.arrow');
  fullscreenIcon.style.display = 'none';
  minimizedIcon.style.display = 'none';
  arrowIcon.style.display = 'inline-block'
}
 

function toggleModalSize() {
  const modalDialog = document.querySelector('.modal-dialog');

  if (modalDialog.classList.contains('modal-xl')) {
    // Maximizing to fullscreen
    modalDialog.classList.remove('modal-xl');
    modalDialog.classList.add('modal-fullscreen');
  } else {
    // Minimizing back to default size
    modalDialog.classList.remove('modal-fullscreen');
    modalDialog.classList.add('modal-xl');
  }
}

function toggleMiniSize() {
  const modalDialog = document.querySelector('.modal-dialog');

  if (modalDialog.classList.contains('modal-xl')) {
      // Maximizing to fullscreen
      modalDialog.classList.remove('modal-xl');
      modalDialog.classList.add('modal-lg');
  } else {
      // Minimizing back to default size
      modalDialog.classList.remove('modal-lg');
      modalDialog.classList.add('modal-xl');
  }
}



//Modal for each row
tableBody.querySelectorAll('tr').forEach(row => {
  row.setAttribute('data-bs-toggle', 'modal')
  row.setAttribute('data-bs-target', '#rowDetailsModal')
  row.addEventListener('click', () => {
    const data = Array.from(row.children).map(cell => cell.innerHTML)
    const modal = document.getElementById('rowDetailsModal');
    modal.querySelector('#name').innerHTML = '#' + data[0]
    modal.querySelector('#category').innerHTML = data[1]
    modal.querySelector('#subcategory').innerHTML = data[2]
    modal.querySelector('#model').innerHTML = data[3]
    modal.querySelector('#serial').innerHTML = data[4]
    modal.querySelector('#asset').innerHTML = data[5]
    modal.querySelector('#log').innerHTML = data[6]
    modal.querySelector('#quantity').innerHTML = data[7]
    modal.querySelector('#unit-price').innerHTML = data[8]
    modal.querySelector('#location').innerHTML = data[13]
    modal.querySelector('#status').innerHTML = data[15]
    modal.style.display = 'block';
  })
})


const rowDetailsModal = document.getElementById('rowDetailsModal');

loadButton.addEventListener('click', () => {

  loader.style.display = 'block';

  setTimeout(() => {
    loader.style.display = 'none';
    rowDetailsModal.show();
  }, 3000);
});



} catch (error) {
  console.log(error)
}

// Javascript Logic for Report

// Javascript Logic for Asset Performance Report
try {
  const assetReportTableBody = document.getElementById('assetReport-tableBody');
const rowCountSelect = document.getElementById('rows')

const assetReportTableData = [
  {
    id: 1,
    items: '1',
    category: '331',
    subCategory: "1KZ04885",
    model: "Generator",
    partNumber: "Generator 1(1250KVA)",
    assetTag: "Ado Bayero Mall Generator Plant",
    serialNumber: "9",
    quantity: "625,112.67",
    unitPrice: "0",
    amount: "0",
    reorderLevel: "11,047,586.23",
    minimum: "0",
    maximum: "0",
    location: "",
  },
  {
    id: 2,
    items: '2',
    category: '331',
    subCategory: "1KZ04885",
    model: "Generator",
    partNumber: "Generator 1(1250KVA)",
    assetTag: "Ado Bayero Mall Generator Plant",
    serialNumber: "9",
    quantity: "625,112.67",
    unitPrice: "0",
    amount: "0",
    reorderLevel: "11,047,586.23",
    minimum: "0",
    maximum: "0",
    location: "",
  },
  {
    id: 3,
    items: '3',
    category: '331',
    subCategory: "1KZ04885",
    model: "Generator",
    partNumber: "Generator 1(1250KVA)",
    assetTag: "Ado Bayero Mall Generator Plant",
    serialNumber: "9",
    quantity: "625,112.67",
    unitPrice: "0",
    amount: "0",
    reorderLevel: "11,047,586.23",
    minimum: "0",
    maximum: "0",
    location: "",
  },
  {
    id: 4,
    items: '4',
    category: '331',
    subCategory: "1KZ04885",
    model: "Generator",
    partNumber: "Generator 1(1250KVA)",
    assetTag: "Ado Bayero Mall Generator Plant",
    serialNumber: "9",
    quantity: "625,112.67",
    unitPrice: "0",
    amount: "0",
    reorderLevel: "11,047,586.23",
    minimum: "0",
    maximum: "0",
    location: "",
  },
  {
    id: 5,
    items: '5',
    category: '331',
    subCategory: "1KZ04885",
    model: "Generator",
    partNumber: "Generator 1(1250KVA)",
    assetTag: "Ado Bayero Mall Generator Plant",
    serialNumber: "9",
    quantity: "625,112.67",
    unitPrice: "0",
    amount: "0",
    reorderLevel: "11,047,586.23",
    minimum: "0",
    maximum: "0",
    location: "",
  },
  {
    id: 6,
    items: '6',
    category: '331',
    subCategory: "1KZ04885",
    model: "Generator",
    partNumber: "Generator 1(1250KVA)",
    assetTag: "Ado Bayero Mall Generator Plant",
    serialNumber: "9",
    quantity: "625,112.67",
    unitPrice: "0",
    amount: "0",
    reorderLevel: "11,047,586.23",
    minimum: "0",
    maximum: "0",
    location: "",
  },
  {
    id: 7,
    items: '7',
    category: '331',
    subCategory: "1KZ04885",
    model: "Generator",
    partNumber: "Generator 1(1250KVA)",
    assetTag: "Ado Bayero Mall Generator Plant",
    serialNumber: "9",
    quantity: "625,112.67",
    unitPrice: "0",
    amount: "0",
    reorderLevel: "11,047,586.23",
    minimum: "0",
    maximum: "0",
    location: "",
  },
  {
    id: 8,
    items: '8',
    category: '331',
    subCategory: "1KZ04885",
    model: "Generator",
    partNumber: "Generator 1(1250KVA)",
    assetTag: "Ado Bayero Mall Generator Plant",
    serialNumber: "9",
    quantity: "625,112.67",
    unitPrice: "0",
    amount: "0",
    reorderLevel: "11,047,586.23",
    minimum: "0",
    maximum: "0",
    location: "",
  },
  {
    id: 9,
    items: '9',
    category: '331',
    subCategory: "1KZ04885",
    model: "Generator",
    partNumber: "Generator 1(1250KVA)",
    assetTag: "Ado Bayero Mall Generator Plant",
    serialNumber: "9",
    quantity: "625,112.67",
    unitPrice: "0",
    amount: "0",
    reorderLevel: "11,047,586.23",
    minimum: "0",
    maximum: "0",
    location: "",
  },
  {
    id: 10,
    items: '10',
    category: '331',
    subCategory: "1KZ04885",
    model: "Generator",
    partNumber: "Generator 1(1250KVA)",
    assetTag: "Ado Bayero Mall Generator Plant",
    serialNumber: "9",
    quantity: "625,112.67",
    unitPrice: "0",
    amount: "0",
    reorderLevel: "11,047,586.23",
    minimum: "0",
    maximum: "0",
    location: "",
  },
  
  
];

function populateTable() {
  assetReportTableData.forEach(item => {
    const row = document.createElement('tr');
  
    const col1 = document.createElement('td');
    col1.innerHTML = item.items;
    col1.classList.add('table-row')
    row.appendChild(col1);
  
    const col2 = document.createElement('td');
    col2.innerHTML = item.category;
    col2.classList.add('table-row')
    row.appendChild(col2);
  
    const col3 = document.createElement('td');
    col3.innerHTML = item.subCategory;
    col3.classList.add('table-row')
    row.appendChild(col3);
  
    const col4 = document.createElement('td');
    col4.innerHTML = item.model;
    col4.classList.add('table-row')
    row.appendChild(col4);
  
    const col5 = document.createElement('td');
    col5.innerHTML = item.partNumber;
    col5.classList.add('table-row')
    row.appendChild(col5);
  
    const col6 = document.createElement('td');
    col6.innerHTML = item.assetTag;
    col6.classList.add('table-row')
    row.appendChild(col6);
  
    const col7 = document.createElement('td');
    col7.innerHTML = item.serialNumber;
    col7.classList.add('table-row')
    row.appendChild(col7);
  
    const col8 = document.createElement('td');
    col8.innerHTML = item.quantity;
    col8.classList.add('table-row')
    row.appendChild(col8);
  
    const col9 = document.createElement('td');
    col9.innerHTML = item.unitPrice;
    col9.classList.add('table-row')
    row.appendChild(col9);
  
    const col10 = document.createElement('td');
    col10.innerHTML = item.amount;
    col10.classList.add('table-row')
    row.appendChild(col10);
  
    const col11 = document.createElement('td');
    col11.innerHTML = item.reorderLevel
    col11.classList.add('table-row')
    row.appendChild(col11);
  
    const col12 = document.createElement('td');
    col12.innerHTML = item.minimum;
    col12.classList.add('table-row')
    row.appendChild(col12);
  
    const col13 = document.createElement('td');
    col13.innerHTML = item.maximum;
    col13.classList.add('table-row')
    row.appendChild(col13);
  
    const col14 = document.createElement('td');
    col14.innerHTML = item.location;
    col14.classList.add('table-row')
    row.appendChild(col14);
  
    assetReportTableBody.appendChild(row);
  })
}

function updateRows() {
  const rowCount = parseInt(rowCountSelect.value);
  const rows = assetReportTableBody.children;
  for (let i = 0; i < rows.length; i++) {
    if (i < rowCount) {
      rows[i].style.display = ''; // Show the row
    } else {
      rows[i].style.display = 'none'; // Hide the row
    }
  }
}

rowCountSelect.addEventListener('change', updateRows);

populateTable();

//Logic for the spinner and the modal
const loadButton = document.getElementById('load-button');
const loader = document.getElementById('loader');
const myModal = new bootstrap.Modal(document.getElementById('ExtralargeModal'));

loadButton.addEventListener('click', () => {

  loader.style.display = 'block';

  setTimeout(() => {
    loader.style.display = 'none';
    myModal.show();
  }, 3000);
});

//Logic for search functionality

function searchTable() {
  const searchQuery = document.getElementById('searchInput').value.toLowerCase();

  const rows = tableBody.children;

  for (let i = 0; i < rows.length; i++) {
    const rowData = rows[i].innerText.toLowerCase();
    if (rowData.includes(searchQuery)) {
      rows[i].style.display = ''; // Show the row if it matches the search query
    } else {
      rows[i].style.display = 'none'; // Hide the row if it doesn't match
    }
  }
}

//Logic for the minimize and maximize functionality for both modals

function showIcons() {
  const fullscreenIcon = document.querySelector('.fullscreen');
  const minimizedIcon = document.querySelector('.minimized');
  const arrowIcon = document.querySelector('.arrow');
  fullscreenIcon.style.display = 'inline-block';
  minimizedIcon.style.display = 'inline-block';
  arrowIcon.style.display = 'none'
}

function hideIcons() {
  const fullscreenIcon = document.querySelector('.fullscreen');
  const minimizedIcon = document.querySelector('.minimized');
  const arrowIcon = document.querySelector('.arrow');
  fullscreenIcon.style.display = 'none';
  minimizedIcon.style.display = 'none';
  arrowIcon.style.display = 'inline-block'
}
 

function toggleModalSize() {
  const modalDialog = document.querySelector('.modal-dialog');

  if (modalDialog.classList.contains('modal-xl')) {
    // Maximizing to fullscreen
    modalDialog.classList.remove('modal-xl');
    modalDialog.classList.add('modal-fullscreen');
  } else {
    // Minimizing back to default size
    modalDialog.classList.remove('modal-fullscreen');
    modalDialog.classList.add('modal-xl');
  }
}

function toggleMiniSize() {
  const modalDialog = document.querySelector('.modal-dialog');

  if (modalDialog.classList.contains('modal-xl')) {
      // Maximizing to fullscreen
      modalDialog.classList.remove('modal-xl');
      modalDialog.classList.add('modal-lg');
  } else {
      // Minimizing back to default size
      modalDialog.classList.remove('modal-lg');
      modalDialog.classList.add('modal-xl');
  }
}



//Modal for each row
tableBody.querySelectorAll('tr').forEach(row => {
  row.setAttribute('data-bs-toggle', 'modal')
  row.setAttribute('data-bs-target', '#rowDetailsModal')
  row.addEventListener('click', () => {
    const data = Array.from(row.children).map(cell => cell.innerHTML)
    const modal = document.getElementById('rowDetailsModal');
    modal.querySelector('#name').innerHTML = '#' + data[0]
    modal.querySelector('#category').innerHTML = data[1]
    modal.querySelector('#subcategory').innerHTML = data[2]
    modal.querySelector('#model').innerHTML = data[3]
    modal.querySelector('#serial').innerHTML = data[4]
    modal.querySelector('#asset').innerHTML = data[5]
    modal.querySelector('#log').innerHTML = data[6]
    modal.querySelector('#quantity').innerHTML = data[7]
    modal.querySelector('#unit-price').innerHTML = data[8]
    modal.querySelector('#location').innerHTML = data[13]
    modal.querySelector('#status').innerHTML = data[15]
    modal.style.display = 'block';
  })
})


const rowDetailsModal = document.getElementById('rowDetailsModal');

loadButton.addEventListener('click', () => {

  loader.style.display = 'block';

  setTimeout(() => {
    loader.style.display = 'none';
    rowDetailsModal.show();
  }, 3000);
});

} catch (error) {
  console.log(error)  
}

// Javascript Logic for Inventory Summary Report



// Javascript Logic for Reference
// Javascript Logic for Category 

try {
  //Toggle Category Sidebar
let categSidebar = document.querySelector(".categ-sidebar");
let categSidebarBtn = document.querySelector(".categ-sidebarBtn");

categSidebarBtn.addEventListener('click', () => {
    categSidebar.classList.toggle('active');
})

document.addEventListener('DOMContentLoaded', () => {
  const categs = document.querySelectorAll('.categ-name');
  const categContent = document.querySelector('.categ-body_content');
  const defaultImage = document.getElementById('default-image')



  const categDetails = {
      1:{
          name: "Access Control",
          status: "In Progress",
      },
  
      2:{
          name: "Branded Materials",
          status: "Active",
      },

      3:{
          name: "Building Transportation",
          status: "Active",
      },

      4:{
          name: "Branded Materials",
          status: "Active",
      },

      5:{
          name: "Branded Materials",
          status: "Active",
      },

      6:{
          name: "Branded Materials",
          status: "Active",
      },

      7:{
          name: "Branded Materials",
          status: "Active",
      },

      8:{
          name: "Branded Materials",
          status: "Active",
      },
  };


  const displayItemDetails = (details) => {
      document.getElementById('name-type').innerText = details.name;
      document.getElementById('status-type').innerText = details.status;
  }
  
  categs.forEach(item => {
      item.addEventListener('click', () => {
          const itemId = item.dataset.id;
          const details = categDetails[itemId];
  
          if (details) {
              defaultImage.style.display = 'none';
              categContent.style.display = 'block';
              displayItemDetails(details)
          }
      })
  });
})

} catch (error) {
  console.log(error)
}

// Javascript Logic for Subcategory
try {
  //Toggle Subcategory Sidebar
let subCategorySidebar = document.querySelector(".subCategory-sidebar");
let subCategorySidebarBtn = document.querySelector(".subCategory-sidebarBtn");

subCategorySidebarBtn.addEventListener('click', () => {
  subCategorySidebar.classList.toggle('active');
})

document.addEventListener('DOMContentLoaded', () => {
  const subCategories = document.querySelectorAll('.subCategory-sidebar_list');
  const subCategoryContent = document.querySelector('.subCategory-body_content');
  const defaultImage = document.getElementById('default-image')



  const subCategoryDetails = {
      1:{
          code: "SC-3930",
          name: "Access",
          type: "Asset",
          category: "Elvs",
          unit: "Piece",
          store: "No",
          serial: "No",
          part: "No",
          expiry: "No",
          status: "In Progress",
      },
  
      2:{
          code: "SC-3930",
          name: "Access",
          type: "Asset",
          category: "Elvs",
          unit: "Piece",
          store: "No",
          serial: "No",
          part: "No",
          expiry: "No",
          status: "In Progress",
      },

      3:{
          code: "SC-3930",
          name: "Access",
          type: "Asset",
          category: "Elvs",
          unit: "Piece",
          store: "No",
          serial: "No",
          part: "No",
          expiry: "No",
          status: "In Progress",
      },

      4:{
          code: "SC-3930",
          name: "Access",
          type: "Asset",
          category: "Elvs",
          unit: "Piece",
          store: "No",
          serial: "No",
          part: "No",
          expiry: "No",
          status: "In Progress",
      },

      5:{
          code: "SC-3930",
          name: "Access",
          type: "Asset",
          category: "Elvs",
          unit: "Piece",
          store: "No",
          serial: "No",
          part: "No",
          expiry: "No",
          status: "In Progress",
      },

      6:{
          code: "SC-3930",
          name: "Access",
          type: "Asset",
          category: "Elvs",
          unit: "Piece",
          store: "No",
          serial: "No",
          part: "No",
          expiry: "No",
          status: "In Progress",
      },

      7:{
          code: "SC-3930",
          name: "Access",
          type: "Asset",
          category: "Elvs",
          unit: "Piece",
          store: "No",
          serial: "No",
          part: "No",
          expiry: "No",
          status: "In Progress",
      },

      8:{
          code: "SC-3930",
          name: " Access",
          type: "Asset",
          category: "Elvs",
          unit: "Piece",
          store: "No",
          serial: "No",
          part: "No",
          expiry: "No",
          status: "In Progress",
      },
  };


  const displayItemDetails = (details) => {
      document.getElementById('code-type').innerText = details.code
      document.getElementById('name-type').innerText = details.name;
      document.getElementById('type-type').innerText = details.type;
      document.getElementById('category-type').innerText = details.category;
      document.getElementById('unit-type').innerText = details.unit;
      document.getElementById('store-type').innerText = details.store;
      document.getElementById('serial-type').innerText = details.serial;
      document.getElementById('part-type').innerText = details.part;
      document.getElementById('expiry-type').innerText = details.expiry;
      document.getElementById('status-type').innerText = details.status;
  }
  
  subCategories.forEach(item => {
      item.addEventListener('click', () => {
          const itemId = item.dataset.id;
          const details = subCategoryDetails[itemId];
  
          if (details) {
              defaultImage.style.display = 'none';
              subCategoryContent.style.display = 'block';
              displayItemDetails(details)
          }
      })
  });
})
} catch (error) {
  console.log(error)
}

// Javascript Logic for Model

try {
  //Toggle Model Sidebar
let modelSidebar = document.querySelector(".model-sidebar");
let modelSidebarBtn = document.querySelector(".model-sidebarBtn");

modelSidebarBtn.addEventListener('click', () => {
    modelSidebar.classList.toggle('active');
})

document.addEventListener('DOMContentLoaded', () => {
  const models = document.querySelectorAll('.model-sidebar_list');
  const modelContent = document.querySelector('.model-body_content');
  const defaultImage = document.getElementById('default-image')



  const modelDetails = {
      1:{
          name: "10HP LIFT PUMP",
          category: "Living Room",
          manufacturer: "N/A",
          status: "In Progress",
      },
      2:{
          name: "10HP LIFT PUMP",
          category: "Living Room",
          manufacturer: "N/A",
          status: "In Progress",
      },
      3:{
          name: "10HP LIFT PUMP",
          category: "Living Room",
          manufacturer: "N/A",
          status: "In Progress",
      },
      4:{
          name: "10HP LIFT PUMP",
          category: "Living Room",
          manufacturer: "N/A",
          status: "In Progress",
      },
      5:{
          name: "10HP LIFT PUMP",
          category: "Living Room",
          manufacturer: "N/A",
          status: "In Progress",
      },
      6:{
          name: "10HP LIFT PUMP",
          category: "Living Room",
          manufacturer: "N/A",
          status: "In Progress",
      },
      7:{
          name: "10HP LIFT PUMP",
          category: "Living Room",
          manufacturer: "N/A",
          status: "In Progress",
      },
      8:{
          name: "10HP LIFT PUMP",
          category: "Living Room",
          manufacturer: "N/A",
          status: "In Progress",
      },
  
      
  };


  const displayItemDetails = (details) => {
      document.getElementById('name-type').innerText = details.name;
      document.getElementById('subCategory-type').innerText = details.category;
      document.getElementById('manufacturer-type').innerText = details.manufacturer;
      document.getElementById('status-type').innerText = details.status;
  }
  
  models.forEach(item => {
      item.addEventListener('click', () => {
          const itemId = item.dataset.id;
          const details = modelDetails[itemId];
  
          if (details) {
              defaultImage.style.display = 'none';
              modelContent.style.display = 'block';
              displayItemDetails(details)
          }
      })
  });
})
} catch (error) {
  console.log(error)
}

// Javascript Logic for Manufacturer
try {
  //Toggle Manufacturer Sidebar
let manufacturerSidebar = document.querySelector(".manufacturer-sidebar");
let manufacturerSidebarBtn = document.querySelector(".manufacturer-sidebarBtn");

manufacturerSidebarBtn.addEventListener('click', () => {
    manufacturerSidebar.classList.toggle('active');
})

document.addEventListener('DOMContentLoaded', () => {
  const manufacturers = document.querySelectorAll('.manufacturer-sidebar_list');
  const manufacturerContent = document.querySelector('.manufacturer-body_content');
  const defaultImage = document.getElementById('default-image');
  const nameStatusOne = document.getElementById('name-status-one')



  const manufacturerDetails = {
      1:{
          name: nameStatusOne.innerHTML,
          category: "Mechanical",
          status: "Active",
      },
      2:{
          name: "1/4'",
          category: "Mechanical",
          status: "Active",
      },
      3:{
          name: "2451307819",
          category: "Mechanical",
          status: "Active",
      },
      4:{
          name: "3/4'",
          category: "Mechanical",
          status: "In Progress",
      },
      5:{
          name: "3/8'",
          category: "Mechanical",
          status: "In Progress",
      },
      6:{
          name: "5/8'",
          category: "Mechanical",
          status: "In Progress",
      },
      7:{
          name: "Ab",
          category: "Electrical",
          status: "In Progress",
      },
      8:{
          name: "Ab Coaster",
          category: "Recreational",
          status: "In Progress",
      },
  
      
  };


  const displayItemDetails = (details) => {
      document.getElementById('name-type').innerText = details.name;
      document.getElementById('category-type').innerText = details.category;
      document.getElementById('status-type').innerText = details.status;
  }
  
  manufacturers.forEach(item => {
      item.addEventListener('click', () => {
          const itemId = item.dataset.id;
          const details = manufacturerDetails[itemId];
  
          if (details) {
              defaultImage.style.display = 'none';
              manufacturerContent.style.display = 'block';
              displayItemDetails(details)
          }
      })
  });
})
} catch (error) {
  console.log(error)
}

// Javascript Logic for Warehouse

try {
  //Toggle Warehouse Sidebar
let warehouseSidebar = document.querySelector(".warehouse-sidebar");
let wareHouseSidebarBtn = document.querySelector(".warehouse-sidebarBtn");

wareHouseSidebarBtn.addEventListener('click', () => {
    warehouseSidebar.classList.toggle('active');
})

document.addEventListener('DOMContentLoaded', () => {
  const warehouses = document.querySelectorAll('.warehouse-sidebar_list');
  const warehouseContent = document.querySelector('.warehouse-body_content');
  const defaultImage = document.getElementById('default-image');
  const nameStatusOne = document.getElementById('name-status-one')



  const warehouseDetails = {
      1:{
          name: nameStatusOne.innerHTML,
          tank: "No",
          category: "Mechanical",
          status: "Active",
      },
      2:{
          name: "1/4'",
          tank: "No",
          category: "Mechanical",
          status: "Active",
      },
      3:{
          name: "2451307819",
          tank: "No",
          category: "Mechanical",
          status: "Active",
      },
      4:{
          name: "3/4'",
          tank: "No",
          category: "Mechanical",
          status: "In Progress",
      },
      5:{
          name: "3/8'",
          tank: "No",
          category: "Mechanical",
          status: "In Progress",
      },
      6:{
          name: "5/8'",
          tank: "No",
          category: "Mechanical",
          status: "In Progress",
      },
      7:{
          name: "Ab",
          tank: "No",
          category: "Electrical",
          status: "In Progress",
      },
      8:{
          name: "Ab Coaster",
          tank: "No",
          category: "Recreational",
          status: "In Progress",
      },
  
      
  };


  const displayItemDetails = (details) => {
      document.getElementById('name-type').innerText = details.name;
      document.getElementById('category-type').innerText = details.category;
      document.getElementById('status-type').innerText = details.status;
      document.getElementById('tank-type').innerText = details.tank;
  }
  
  warehouses.forEach(item => {
      item.addEventListener('click', () => {
          const itemId = item.dataset.id;
          const details = warehouseDetails[itemId];
  
          if (details) {
              defaultImage.style.display = 'none';
              warehouseContent.style.display = 'block';
              displayItemDetails(details)
          }
      })
  });
})

} catch (error) {
  console.log(error)  
}

// Javascript Logic for Unit of Measurement

try {
  //Toggle Unit Sidebar
let unitSidebar = document.querySelector(".unit-sidebar");
let unitSidebarBtn = document.querySelector(".unit-sidebarBtn");

unitSidebarBtn.addEventListener('click', () => {
    unitSidebar.classList.toggle('active');
})

document.addEventListener('DOMContentLoaded', () => {
  const units = document.querySelectorAll('.unit-sidebar_list');
  const unitsContent = document.querySelector('.unit-body_content');
  const defaultImage = document.getElementById('default-image');



  const unitDetails = {
      1:{
          code: "A",
          description: "Amperes",
          symbol: "Amperes",
          type: "Other",
          status: "Active",
      },
      2:{
          code: "CG",
          description: "Amperes",
          symbol: "Amperes",
          type: "Other",
          status: "Active",
      },
      3:{
          code: "CL",
          description: "Amperes",
          symbol: "Amperes",
          type: "Other",
          status: "Active",
      },
      4:{
          code: "CM",
          description: "Amperes",
          symbol: "Amperes",
          type: "Other",
          status: "Active",
      },
      5:{
          code: "C",
          description: "Amperes",
          symbol: "Amperes",
          type: "Other",
          status: "Active",
      },
      6:{
          code: "CM3",
          description: "Amperes",
          symbol: "Amperes",
          type: "Other",
          status: "Active",
      },
      7:{
          code: "DM3",
          description: "Amperes",
          symbol: "Amperes",
          type: "Other",
          status: "Active",
      }
      
  
      
  };


  const displayItemDetails = (details) => {
      document.getElementById('code-type').innerText = details.code;
      document.getElementById('description-type').innerText = details.description;
      document.getElementById('symbol-type').innerText = details.symbol;
      document.getElementById('type-type').innerText = details.type;
      document.getElementById('status-type').innerText = details.status;
  }
  
  units.forEach(item => {
      item.addEventListener('click', () => {
          const itemId = item.dataset.id;
          const details = unitDetails[itemId];
  
          if (details) {
              defaultImage.style.display = 'none';
              unitsContent.style.display = 'block';
              displayItemDetails(details)
          }
      })
  });
})
} catch (error) {
  console.log(error)
}


// Javascript Logic for Lease Section

//Javascript Logic for Lease

try {
  //Toggle Lease Sidebar
  let leaseSidebar = document.querySelector(".lease-sidebar");
let leaseSidebarBtn = document.querySelector(".lease-sidebarBtn");

leaseSidebarBtn.addEventListener('click', () => {
  leaseSidebar.classList.toggle('active');
})

document.addEventListener('DOMContentLoaded', () => {
  const leases = document.querySelectorAll('.lease-sidebar_content');
  const defaultImage = document.getElementById('default-image');
  const leaseContent = document.querySelector('.lease-body_content');



  const leaseDetails = {
    1:{
      client: 'Rent4Less',
      contactName: 'OLUWATOMIWA AHMED MOROMOKE',
      contactEmail: 'moromokeahmed55@yahoo.com',
      contactPhone: '07018226594',
      status: 'Running',
    },
  };

  
  const displayLeaseDetails = (detail) => {
    document.getElementById('lease-client').innerText = detail.client
    document.getElementById('lease-name').innerText = detail.contactName;
    document.getElementById('lease-email').innerText = detail.contactEmail;
    document.getElementById('lease-phone').innerText = detail.contactPhone;
    document.getElementById('lease-status').innerText = detail.status;
  }
  
  leases.forEach(lease => {
    lease.addEventListener('click', () => {
      const itemIds = lease.dataset.id;
      const detailse = leaseDetails[itemIds];

      if (detailse) {
        defaultImage.style.display = 'none';
        leaseContent.style.display = 'block';
        displayLeaseDetails(detailse)
      }
    })
  });
});
} catch (error) {
  console.log(error)
}


// Javascript Logic for Lease Invoice

try {
  //Toggle Lease Invoice Sidebar
let leaseInvoiceSidebar = document.querySelector(".lease_invoice-sidebar");
let leaseInvoiceSidebarBtn = document.querySelector(".lease_invoice-sidebarBtn");

leaseInvoiceSidebarBtn.addEventListener('click', () => {
    leaseInvoiceSidebar.classList.toggle('active');
})

document.addEventListener('DOMContentLoaded', () => {
  const leaseInvoices = document.querySelectorAll('.lease_invoice-sidebar_content');
  const defaultImage = document.getElementById('default-image');
  const leaseInvoiceContent = document.querySelector('.lease_invoice-body_content');



  const leaseInvoiceDetails = {
      1:{
          client: 'Rent4Less',
          contactName: 'AKPUNWOKE VICTOR',
          invoiceNumber: 'null/00000162/01062024',
          invoiceDate: '01/06/2024',
          vatNumber: '00221306-000010',
          tinNumber: '00221306-000010',
          tax: '0%',
          vatAdded: 'Yes',
          paymentDate: '01/06/2024',
          status: 'Payment pending',
      },
      2:{
          client: 'Rent4Less',
          contactName: 'AKPUNWOKE VICTOR',
          invoiceNumber: 'null/00000162/01062024',
          invoiceDate: '01/06/2024',
          vatNumber: '00221306-000010',
          tinNumber: '00221306-000010',
          tax: '0%',
          vatAdded: 'Yes',
          paymentDate: '01/06/2024',
          status: 'Payment pending',
      },
      3:{
          client: 'Rent4Less',
          contactName: 'AKPUNWOKE VICTOR',
          invoiceNumber: 'null/00000162/01062024',
          invoiceDate: '01/06/2024',
          vatNumber: '00221306-000010',
          tinNumber: '00221306-000010',
          tax: '0%',
          vatAdded: 'Yes',
          paymentDate: '01/06/2024',
          status: 'Payment pending',
      },
      4:{
          client: 'Rent4Less',
          contactName: 'AKPUNWOKE VICTOR',
          invoiceNumber: 'null/00000162/01062024',
          invoiceDate: '01/06/2024',
          vatNumber: '00221306-000010',
          tinNumber: '00221306-000010',
          tax: '0%',
          vatAdded: 'Yes',
          paymentDate: '01/06/2024',
          status: 'Payment pending',
      },
      5:{
          client: 'Rent4Less',
          contactName: 'AKPUNWOKE VICTOR',
          invoiceNumber: 'null/00000162/01062024',
          invoiceDate: '01/06/2024',
          vatNumber: '00221306-000010',
          tinNumber: '00221306-000010',
          tax: '0%',
          vatAdded: 'Yes',
          paymentDate: '01/06/2024',
          status: 'Payment pending',
      },
  };

  
  const displayItemDetails = (details) => {
      document.getElementById('client').innerText = details.client
      document.getElementById('c-name').innerText = details.contactName;
      document.getElementById('invoice-number').innerText = details.invoiceNumber;
      document.getElementById('invoice-date').innerText = details.invoiceDate;
      document.getElementById('vat-number').innerText = details.vatNumber;
      document.getElementById('tin-number').innerText = details.tinNumber;
      document.getElementById('tax').innerText = details.tax;
      document.getElementById('vat-added').innerText = details.vatAdded;
      document.getElementById('payment-date').innerText = details.paymentDate;
      document.getElementById('item-status').innerText = details.status;
  }
  
  leaseInvoices.forEach(invoice => {
      invoice.addEventListener('click', () => {
          const itemId = invoice.dataset.id;
          const details = leaseInvoiceDetails[itemId];
  
          if (details) {
              defaultImage.style.display = 'none';
              leaseInvoiceContent.style.display = 'block';
              displayItemDetails(details)
          }
      })
  });
})
} catch (error) {
  console.log(error)
}

// Javascript Logic for Lease Reference

// Javascript Logic for Agency
try {
  //Toggle Agency Sidebar
let agencySidebar = document.querySelector(".agency-sidebar");
let agencySidebarBtn = document.querySelector(".agency-sidebarBtn");

agencySidebarBtn.addEventListener('click', () => {
    agencySidebar.classList.toggle('active');
})
} catch (error) {
  console.log(error)
}

// Javascript Logic for Solicitor
try {
  //Toggle Solicitor Sidebar
let solicitorSidebar = document.querySelector(".solicitor-sidebar");
let solicitorSidebarBtn = document.querySelector(".solicitor-sidebarBtn");

solicitorSidebarBtn.addEventListener('click', () => {
    solicitorSidebar.classList.toggle('active');
})
} catch (error) {
  console.log(error)
}

// Javascript Logic for Fee Type

try {
  //Toggle Fee Type Sidebar
let feeTypeSidebar = document.querySelector(".feeType-sidebar");
let feeTypeSidebarBtn = document.querySelector(".feeType-sidebarBtn");

feeTypeSidebarBtn.addEventListener('click', () => {
    feeTypeSidebar.classList.toggle('active');
})

document.addEventListener('DOMContentLoaded', () => {
  const feeTypes = document.querySelectorAll('.feeType-sidebar_content');
  const defaultImage = document.getElementById('default-image');
  const feeTypeContent = document.querySelector('.feeType-body_content');



  const feeTypeDetails = {
      1:{
          name: 'Agency Fee',
          description: '',
          type: 'Fee',
          payable: 'Agency',
          status: 'Active',
      },
      2:{
          name: 'Agency Fee',
          description: '',
          type: 'Fee',
          payable: 'Agency',
          status: 'Active',
      },
      3:{
          name: 'Agency Fee',
          description: '',
          type: 'Fee',
          payable: 'Agency',
          status: 'Active',
      },
      4:{
          name: 'Agency Fee',
          description: '',
          type: 'Fee',
          payable: 'Agency',
          status: 'Active',
      },
      5:{
          name: 'Agency Fee',
          description: '',
          type: 'Fee',
          payable: 'Agency',
          status: 'Active',
      },
      
      
  };

  
  const displayItemDetails = (details) => {
      document.getElementById('fee-name').innerText = details.name;
      document.getElementById('fee-description').innerText = details.description;
      document.getElementById('fee-type').innerText = details.type;
      document.getElementById('payable').innerText = details.payable;
      document.getElementById('feeType-status').innerText = details.status;
  }
  
  feeTypes.forEach(item => {
      item.addEventListener('click', () => {
          const itemId = item.dataset.id;
          const details = feeTypeDetails[itemId];
  
          if (details) {
              defaultImage.style.display = 'none';
              feeTypeContent.style.display = 'block';
              displayItemDetails(details)
          }
      })
  });
})
} catch (error) {
  console.log(error)
}

// Javascript Logic for Procurement Section

// Javascript Logic for Request for Quotation
try {
  //Toggle Subcategory Sidebar

document.addEventListener('DOMContentLoaded', () => {
  const sidebarContent = document.querySelector('.quotation-sidebar_contents');
  const quotationContent = document.querySelector('.quotation-body_content');
  const defaultImage = document.getElementById('default-image')
  const loadMoreBtn = document.getElementById('loadMoreBtn');
  const quotationCount = document.getElementById('quotationCount');

  let quotationSidebar = document.querySelector(".quotation-sidebar");
  let quotationSidebarBtn = document.querySelector(".quotation-sidebarBtn");

  quotationSidebarBtn.addEventListener('click', () => {
    quotationSidebar.classList.toggle('active');
  })


  const quotationDetails = {
    1:{
      number: "0000033",
      type: "Item",
      title: "Cleaning Consumables for March 2022",
      submit: "25/03/2022",
      facility: "MTN COTE D'IVOIRE",
      currency: "XOF",
      deadline: "27/03/2022 08:52 AM",
      status: "Submitted",
    },

    2:{
      number: "0000033",
      type: "Item",
      title: "Cleaning Consumables for March 2022",
      submit: "25/03/2022",
      facility: "MTN COTE D'IVOIRE",
      currency: "XOF",
      deadline: "27/03/2022 08:52 AM",
      status: "Submitted",
    },

    3:{
      number: "0000033",
      type: "Item",
      title: "Cleaning Consumables for March 2022",
      submit: "25/03/2022",
      facility: "MTN COTE D'IVOIRE",
      currency: "XOF",
      deadline: "27/03/2022 08:52 AM",
      status: "Submitted",
    },

    4:{
      number: "0000033",
      type: "Item",
      title: "Cleaning Consumables for March 2022",
      submit: "25/03/2022",
      facility: "MTN COTE D'IVOIRE",
      currency: "XOF",
      deadline: "27/03/2022 08:52 AM",
      status: "Submitted",
    },

    5:{
      number: "0000033",
      type: "Item",
      title: "Cleaning Consumables for March 2022",
      submit: "25/03/2022",
      facility: "MTN COTE D'IVOIRE",
      currency: "XOF",
      deadline: "27/03/2022 08:52 AM",
      status: "Submitted",
    },

    6:{
      number: "0000033",
      type: "Item",
      title: "Cleaning Consumables for March 2022",
      submit: "25/03/2022",
      facility: "MTN COTE D'IVOIRE",
      currency: "XOF",
      deadline: "27/03/2022 08:52 AM",
      status: "Submitted",
    },

    7:{
      number: "0000033",
      type: "Item",
      title: "Cleaning Consumables for March 2022",
      submit: "25/03/2022",
      facility: "MTN COTE D'IVOIRE",
      currency: "XOF",
      deadline: "27/03/2022 08:52 AM",
      status: "Submitted",
    },

    8:{
      number: "0000033",
      type: "Item",
      title: "Cleaning Consumables for March 2022",
      submit: "25/03/2022",
      facility: "MTN COTE D'IVOIRE",
      currency: "XOF",
      deadline: "27/03/2022 08:52 AM",
      status: "Submitted",
    },

    9:{
      number: "0000033",
      type: "Item",
      title: "Cleaning Consumables for March 2022",
      submit: "25/03/2022",
      facility: "MTN COTE D'IVOIRE",
      currency: "XOF",
      deadline: "27/03/2022 08:52 AM",
      status: "Submitted",
    },

    10:{
      number: "0000033",
      type: "Item",
      title: "Cleaning Consumables for March 2022",
      submit: "25/03/2022",
      facility: "MTN COTE D'IVOIRE",
      currency: "XOF",
      deadline: "27/03/2022 08:52 AM",
      status: "Submitted",
    },

    11:{
      number: "0000033",
      type: "Item",
      title: "Cleaning Consumables for March 2022",
      submit: "25/03/2022",
      facility: "MTN COTE D'IVOIRE",
      currency: "XOF",
      deadline: "27/03/2022 08:52 AM",
      status: "Submitted",
    },
    
  };


  const displayItemDetails = (details) => {
    document.getElementById('number').innerText = details.number;
    document.getElementById('type').innerText = details.type;
    document.getElementById('title').innerText = details.title;
    document.getElementById('submit-date').innerText = details.ssubmit;
    document.getElementById('facility').innerText = details.facility;
    document.getElementById('currency').innerText = details.currency;
    document.getElementById('deadline-date').innerText = details.deadline;
    document.getElementById('status').innerText = details.status;
  }
  
  sidebarContent.addEventListener('click', (event) => {
    const clickedItem = event.target.closest('.quotation-sidebar_content');
    if (clickedItem) {
      const itemId = clickedItem.dataset.id;
      const details = quotationDetails[itemId];
      if (details) {
        defaultImage.style.display = 'none';
        quotationContent.style.display = 'block';
        displayItemDetails(details);
      }
    }
  });

  // Sample data to mimic multiple work order items
  const quotations = [
    { id: 1, name: '0000033', duration: "MTN COTE D'IVOIRE", description: 'Cleaning Consumables ', status: '25/03/2022' },
    { id: 2, name: '0000032', duration: 'International Business', description: 'Payment to Nicolas', status: '16/03/2022' },
    { id: 3, name: '0000031', duration: 'International Business', description: 'Payment to Alfred', status: '16/03/2022' },
    { id: 4, name: '0000030', duration: 'Green Park', description: 'SECURITY SERVICES', status: '10/02/2022' },
    { id: 5, name: '0000029', duration: 'Centre Heights', description: 'Complete 2hp Outdoor Unit', status: '10/02/2022' },
    { id: 6, name: '0000028', duration: 'AMDC', description: 'Consultancy Services', status: '10/02/2022' },
    { id: 7, name: '0000027', duration: 'Test Facility', description: 'Quotation for 10A', status: '26/01/2022' },
    { id: 8, name: '0000026', duration: 'New Head Office', description: 'Electrical circuit breaker', status: '24/11/2021' },
    { id: 9, name: '0000025', duration: 'New Head Office', description: 'Test Request', status: '23/11/2021' },
    { id: 10, name: '0000024', duration: 'Test Facility', description: 'test', status: '15/09/2021' },
    { id: 11, name: '0000023', duration: 'Test Facility', description: 'TEST Electrical', status: '09/09/2021' },
    { id: 12, name: '0000022', duration: 'Test Facility', description: 'TEST Electrical', status: '06/09/2021' },
  ];

  // Number of work orders to show initially
  let quotationToShow = 10;




  // Function to render work orders
  function renderQuotation() {
    // Clear current contents
    sidebarContent.innerHTML = '';
    

    // Render the number of work orders specified by workOrdersToShow
    quotations.slice(0, quotationToShow).forEach(order => {
      const content = `
        <div class="quotation-sidebar_content" data-id="${order.id}">
          <div class="quotation-name">
            <span>${order.name}</span>
            <h6>${order.duration}</h6>
          </div>
          <div class="quotation-status">
            <h6>${order.description}</h6>
            <h6>${order.status}</h6>
          </div>
        </div>
      `;
      sidebarContent.insertAdjacentHTML('beforeend', content);
    });
    quotationCount.textContent = `Showing 1 - ${quotationToShow} of ${quotations.length}`;

  
  }

  // Event listener for the "Load More" button
  loadMoreBtn.addEventListener('click', () => {
    // Increase the number of work orders to show by 5
    quotationToShow += 5;

    // If the number of work orders to show exceeds the total, hide the button
    if (quotationToShow >= quotations.length) {
      quotationToShow = quotations.length;
      // loadMoreBtn.style.display = 'none';
    }

    // Render the updated work orders
    renderQuotations();
  });

  // Initial render
  renderQuotation();

})
} catch (error) {
  console.log(error)
}

// Javascript Logic for Purchase Order
try {
  //Toggle Subcategory Sidebar

document.addEventListener('DOMContentLoaded', () => {
  const sidebarContent = document.querySelector('.purchase-sidebar_contents');
  const purchaseContent = document.querySelector('.purchase-body_content');
  const defaultImage = document.getElementById('default-image')
  const loadMoreBtn = document.getElementById('loadMoreBtn');
  const purchaseCount = document.getElementById('purchaseCount');

  let purchaseSidebar = document.querySelector(".purchase-sidebar");
  let purchaseSidebarBtn = document.querySelector(".purchase-sidebarBtn");

  purchaseSidebarBtn.addEventListener('click', () => {
    purchaseSidebar.classList.toggle('active');
  })




  const purchaseDetails = {
    1:{
      number: "0000043",
      date: "23/09/2024",
      type: "Item",
      facility: "1004 (Cluster A)",
      request: "23/09/2024",
      requester: "Chinasa Arikaibe",
      vendor: "Un-Registered Vendors",
      expect: "20/09/2024",
      status: "Approved",
    },

    2:{
      number: "0000043",
      date: "23/09/2024",
      type: "Item",
      facility: "1004 (Cluster A)",
      request: "23/09/2024",
      requester: "Chinasa Arikaibe",
      vendor: "Un-Registered Vendors",
      expect: "20/09/2024",
      status: "Approved",
    },

    3:{
      number: "0000043",
      date: "23/09/2024",
      type: "Item",
      facility: "1004 (Cluster A)",
      request: "23/09/2024",
      requester: "Chinasa Arikaibe",
      vendor: "Un-Registered Vendors",
      expect: "20/09/2024",
      status: "Approved",
    },

    4:{
      number: "0000043",
      date: "23/09/2024",
      type: "Item",
      facility: "1004 (Cluster A)",
      request: "23/09/2024",
      requester: "Chinasa Arikaibe",
      vendor: "Un-Registered Vendors",
      expect: "20/09/2024",
      status: "Approved",
    },

    5:{
      number: "0000043",
      date: "23/09/2024",
      type: "Item",
      facility: "1004 (Cluster A)",
      request: "23/09/2024",
      requester: "Chinasa Arikaibe",
      vendor: "Un-Registered Vendors",
      expect: "20/09/2024",
      status: "Approved",
    },

    6:{
      number: "0000043",
      date: "23/09/2024",
      type: "Item",
      facility: "1004 (Cluster A)",
      request: "23/09/2024",
      requester: "Chinasa Arikaibe",
      vendor: "Un-Registered Vendors",
      expect: "20/09/2024",
      status: "Approved",
    },

    7:{
      number: "0000043",
      date: "23/09/2024",
      type: "Item",
      facility: "1004 (Cluster A)",
      request: "23/09/2024",
      requester: "Chinasa Arikaibe",
      vendor: "Un-Registered Vendors",
      expect: "20/09/2024",
      status: "Approved",
    },

    8:{
      number: "0000043",
      date: "23/09/2024",
      type: "Item",
      facility: "1004 (Cluster A)",
      request: "23/09/2024",
      requester: "Chinasa Arikaibe",
      vendor: "Un-Registered Vendors",
      expect: "20/09/2024",
      status: "Approved",
    },

    9:{
      number: "0000043",
      date: "23/09/2024",
      type: "Item",
      facility: "1004 (Cluster A)",
      request: "23/09/2024",
      requester: "Chinasa Arikaibe",
      vendor: "Un-Registered Vendors",
      expect: "20/09/2024",
      status: "Approved",
    },

    10:{
      number: "0000043",
      date: "23/09/2024",
      type: "Item",
      facility: "1004 (Cluster A)",
      request: "23/09/2024",
      requester: "Chinasa Arikaibe",
      vendor: "Un-Registered Vendors",
      expect: "20/09/2024",
      status: "Approved",
    },

    11:{
      number: "0000043",
      date: "23/09/2024",
      type: "Item",
      facility: "1004 (Cluster A)",
      request: "23/09/2024",
      requester: "Chinasa Arikaibe",
      vendor: "Un-Registered Vendors",
      expect: "20/09/2024",
      status: "Approved",
    },
    
  };


  const displayItemDetails = (details) => {
    document.getElementById('number').innerText = details.number;
    document.getElementById('date').innerText = details.date;
    document.getElementById('type').innerText = details.type;
    document.getElementById('facility').innerText = details.facility;
    document.getElementById('request-date').innerText = details.request;
    document.getElementById('requester').innerText = details.requester;
    document.getElementById('vendor').innerText = details.vendor;
    document.getElementById('expect').innerText = details.expect;
    document.getElementById('status').innerText = details.status;
  }
  
  sidebarContent.addEventListener('click', (event) => {
    const clickedItem = event.target.closest('.purchase-sidebar_content');
    if (clickedItem) {
      const itemId = clickedItem.dataset.id;
      const details = purchaseDetails[itemId];
      if (details) {
        defaultImage.style.display = 'none';
        purchaseContent.style.display = 'block';
        displayItemDetails(details);
      }
    }
  });

  // Sample data to mimic multiple work order items
const purchases = [
  { id: 1, name: '0000033', duration: "MTN COTE D'IVOIRE", description: 'Cleaning Consumables ', status: '25/03/2022' },
  { id: 2, name: '0000032', duration: 'International Business', description: 'Payment to Nicolas', status: '16/03/2022' },
  { id: 3, name: '0000031', duration: 'International Business', description: 'Payment to Alfred', status: '16/03/2022' },
  { id: 4, name: '0000030', duration: 'Green Park', description: 'SECURITY SERVICES', status: '10/02/2022' },
  { id: 5, name: '0000029', duration: 'Centre Heights', description: 'Complete 2hp Outdoor Unit', status: '10/02/2022' },
  { id: 6, name: '0000028', duration: 'AMDC', description: 'Consultancy Services', status: '10/02/2022' },
  { id: 7, name: '0000027', duration: 'Test Facility', description: 'Quotation for 10A', status: '26/01/2022' },
  { id: 8, name: '0000026', duration: 'New Head Office', description: 'Electrical circuit breaker', status: '24/11/2021' },
  { id: 9, name: '0000025', duration: 'New Head Office', description: 'Test Request', status: '23/11/2021' },
  { id: 10, name: '0000024', duration: 'Test Facility', description: 'test', status: '15/09/2021' },
  { id: 11, name: '0000023', duration: 'Test Facility', description: 'TEST Electrical', status: '09/09/2021' },
  { id: 12, name: '0000022', duration: 'Test Facility', description: 'TEST Electrical', status: '06/09/2021' },
];

// Number of work orders to show initially
let purchaseToShow = 10;

// Function to render work orders
function renderPurchase() {
  // Clear current contents
  sidebarContent.innerHTML = '';
  

  // Render the number of work orders specified by workOrdersToShow
  purchases.slice(0, purchaseToShow).forEach(order => {
    const content = `
      <div class="purchase-sidebar_content" data-id="${order.id}">
        <div class="purchase-name">
          <span>${order.name}</span>
          <h6>${order.duration}</h6>
        </div>
        <div class="purchase-status">
          <h6>${order.description}</h6>
          <h6>${order.status}</h6>
        </div>
      </div>
    `;
    sidebarContent.insertAdjacentHTML('beforeend', content);
  });
  purchaseCount.textContent = `Showing 1 - ${purchaseToShow} of ${purchases.length}`;

  
}

// Event listener for the "Load More" button
loadMoreBtn.addEventListener('click', () => {
  // Increase the number of work orders to show by 5
  purchaseToShow += 5;

  // If the number of work orders to show exceeds the total, hide the button
  if (purchaseToShow >= purchases.length) {
    purchaseToShow = purchases.length;
    // loadMoreBtn.style.display = 'none';
  }

  // Render the updated work orders
  renderPurchases();
});

// Initial render
  renderPurchase();

})
} catch (error) {
  console.log(error)
}

// Javascript Logic for Goods received note
try {
  //Toggle Subcategory Sidebar

document.addEventListener('DOMContentLoaded', () => {
  const sidebarContent = document.querySelector('.goods-sidebar_contents');
  const goodsContent = document.querySelector('.goods-body_content');
  const defaultImage = document.getElementById('default-image')
  const loadMoreBtn = document.getElementById('loadMoreBtn');
  const goodsCount = document.getElementById('goodsCount');

  let goodsSidebar = document.querySelector(".goods-sidebar");
  let goodsSidebarBtn = document.querySelector(".goods-sidebarBtn");

  goodsSidebarBtn.addEventListener('click', () => {
    goodsSidebar.classList.toggle('active');
  })




  const goodsDetails = {
    1:{
      number: "0000002",
      order: "0000002",
      vendor: "ENERGY REINVENTION SERVICES LIMITED",
      receiver: "Facility/Location Store",
      facility: "Test Facility",
      requester: "Josephine Test",
      date: "15/09/2021",
      time: "12:24 PM",
      approve: "No",
      status: "New",
    }
  };


  const displayItemDetails = (details) => {
    document.getElementById('number').innerText = details.number;
    document.getElementById('order').innerText = details.order;
    document.getElementById('vendor').innerText = details.vendor;
    document.getElementById('receiver').innerText = details.receiver;
    document.getElementById('facility').innerText = details.facility;
    document.getElementById('requester').innerText = details.requester;
    document.getElementById('date').innerText = details.date;
    document.getElementById('time').innerText = details.time;
    document.getElementById('approve').innerText = details.approve;
    document.getElementById('status').innerText = details.status;
  }
  
  sidebarContent.addEventListener('click', (event) => {
    const clickedItem = event.target.closest('.goods-sidebar_content');
    if (clickedItem) {
      const itemId = clickedItem.dataset.id;
      const details = goodsDetails[itemId];
      if (details) {
        defaultImage.style.display = 'none';
        goodsContent.style.display = 'block';
        displayItemDetails(details);
      }
    }
  });

  // Sample data to mimic multiple work order items
const goods = [
  { id: 1, name: '0000002', duration: "Test Facility", description: 'Facility', status: 'New' },
];

// Number of work orders to show initially
let goodsToShow = 10;

// Function to render work orders
function renderGoodNotes() {
  // Clear current contents
  sidebarContent.innerHTML = '';
  

  // Render the number of work orders specified by workOrdersToShow
  goods.slice(0, goodsToShow).forEach(order => {
    const content = `
      <div class="goods-sidebar_content" data-id="${order.id}">
        <div class="goods-name">
          <span>${order.name}</span>
          <h6>${order.duration}</h6>
        </div>
        <div class="goods-status">
          <h6>${order.description}</h6>
          <h6>${order.status}</h6>
        </div>
      </div>
    `;
    sidebarContent.insertAdjacentHTML('beforeend', content);
  });
  goodsCount.textContent = `Showing 1 - ${goodsToShow} of ${goods.length}`;

  
}

// Event listener for the "Load More" button
loadMoreBtn.addEventListener('click', () => {
  // Increase the number of work orders to show by 5
  goodsToShow += 5;

  // If the number of work orders to show exceeds the total, hide the button
  if (goodsToShow >= goods.length) {
    goodsToShow = goods.length;
    // loadMoreBtn.style.display = 'none';
  }

  // Render the updated work orders
  renderGoods();
});

// Initial render
  renderGoodNotes();

})
} catch (error) {
  console.log(error)
}

// Javascript Logic for Purchase order requisition
try {
  //Toggle Subcategory Sidebar

document.addEventListener('DOMContentLoaded', () => {
  const sidebarContent = document.querySelector('.order-sidebar_contents');
  const orderContent = document.querySelector('.order-body_content');
  const defaultImage = document.getElementById('default-image')
  const loadMoreBtn = document.getElementById('loadMoreBtn');
  const orderCount = document.getElementById('orderCount');

  let orderSidebar = document.querySelector(".order-sidebar");
  let orderSidebarBtn = document.querySelector(".order-sidebarBtn");

  orderSidebarBtn.addEventListener('click', () => {
    orderSidebar.classList.toggle('active');
  })

  const orderDetails = {
    1:{
      number: "0000002",
      order: "0000002",
      vendor: "ENERGY REINVENTION SERVICES LIMITED",
      receiver: "Facility/Location Store",
      facility: "Test Facility",
      requester: "Josephine Test",
      date: "15/09/2021",
      time: "12:24 PM",
      approve: "No",
      status: "New",
    }
  };


  const displayItemDetails = (details) => {
    document.getElementById('number').innerText = details.number;
    document.getElementById('order').innerText = details.order;
    document.getElementById('vendor').innerText = details.vendor;
    document.getElementById('receiver').innerText = details.receiver;
    document.getElementById('facility').innerText = details.facility;
    document.getElementById('requester').innerText = details.requester;
    document.getElementById('date').innerText = details.date;
    document.getElementById('time').innerText = details.time;
    document.getElementById('approve').innerText = details.approve;
    document.getElementById('status').innerText = details.status;
  }
  
  sidebarContent.addEventListener('click', (event) => {
    const clickedItem = event.target.closest('.order-sidebar_content');
    if (clickedItem) {
      const itemId = clickedItem.dataset.id;
      const details = orderDetails[itemId];
      if (details) {
        defaultImage.style.display = 'none';
        orderContent.style.display = 'block';
        displayItemDetails(details);
      }
    }
  });

  // Sample data to mimic multiple work order items
// const orders = [
//   { id: 1, name: '0000002', duration: "Test Facility", description: 'Facility', status: 'New' },
// ];

// Number of work orders to show initially
let orderToShow = 10;

// Function to render work orders
// function renderOrder() {
//   // Clear current contents
//   sidebarContent.innerHTML = '';
  

  // Render the number of work orders specified by workOrdersToShow
  // orders.slice(0, orderToShow).forEach(item => {
  //   const content = `
  //     <div class="order-sidebar_content" data-id="${item.id}">
  //       <div class="order-name">
  //         <span>${item.name}</span>
  //         <h6>${item.duration}</h6>
  //       </div>
  //       <div class="order-status">
  //         <h6>${item.description}</h6>
  //         <h6>${item.status}</h6>
  //       </div>
  //     </div>
  //   `;
  //   sidebarContent.insertAdjacentHTML('beforeend', content);
  // });
  // orderCount.textContent = `Showing 1 - ${orderToShow} of ${orders.length}`;

  
// }

// Event listener for the "Load More" button
loadMoreBtn.addEventListener('click', () => {
  // Increase the number of work orders to show by 5
  orderToShow += 5;

  // If the number of work orders to show exceeds the total, hide the button
  if (orderToShow >= orders.length) {
    orderToShow = orders.length;
    // loadMoreBtn.style.display = 'none';
  }

  // Render the updated work orders
  renderOrder();
});

// Initial render
  renderOrder();

})
} catch (error) {
  console.log(error)
}

// Javascript Logic for Facility Section

// Javascript Logic for Facility
try {
  document.addEventListener('DOMContentLoaded', () => {
    const sidebarContent = document.querySelector('.location-sidebar_contents');
    const locationContent = document.querySelector('.location-sidebar_subContents');
    const buildingContent = document.querySelector('.building-main_content');
    const roomContent = document.querySelector('.room-main_content');
    const roomContentDetails = document.querySelector('.room-sidebar_contents');
    const loadMoreBtn = document.querySelector('.loadMoreBtn');
    const goodsCount = document.querySelector('.goods-count');
    const buildingsCount = document.querySelector('.buildings-count');
    const roomsCount = document.querySelector('.room-count');

    const locations = [
      {
        id: 1,
        name: '1 Moore Road',
        duration: "Commercial",
        description: 'MO0001',
        status: 'Active',
        buildings: [
          {
            id: 101,
            name: 'Block 1-COMMON AREA 1',
            description: 'BL1',
            status: 'Active',
            apartment: [
              {
                id: 201,
                name: 'Gate House - Gate House',
                description: 'Gate House',
                category: 'Room',
                status: 'Active',
              },
            ],
          },
          { id: 102, name: 'Block 1-COMMON AREA 2', description: 'BL2', status: 'Active' },
          { id: 103, name: 'Block 2-COMMON AREA 2', description: 'BIK2', status: 'Active' },
          { id: 104, name: 'Block 3-COMMON AREA 3', description: 'BLk3', status: 'Active' },
          { id: 105, name: 'Block 4-COMMON AREA 10', description: 'BLK4', status: 'Active' },
          { id: 106, name: 'Block 4-COMMON AREA 11', description: 'BCK11', status: 'Active' },
          { id: 107, name: 'Block 4-COMMON AREA 11', description: 'BCK11', status: 'Active' },
        ],
      },
      {
        id: 2,
        name: '1004 (Cluster A)',
        duration: "Commercial",
        description: '1004EM001',
        status: 'Active',
      },
      {
        id: 3,
        name: '1004 (Cluster B)',
        duration: "Commercial",
        description: '1004EM001',
        status: 'Active',
      },
      {
        id: 4,
        name: '1004 (Cluster C)',
        duration: "Commercial",
        description: '1004EM001',
        status: 'Active',
        buildings: [
          { id: 201, name: 'Building A', description: '3rd Floor', status: 'Active' },
        ],
      },
      {
        id: 5,
        name: '1004 (Cluster D)',
        duration: "Commercial",
        description: '1004EM001',
        status: 'Active',
        buildings: [
          { id: 201, name: 'Building A', description: '3rd Floor', status: 'Active' },
        ],
      },
      {
        id: 6,
        name: '1004 (Shared Services)',
        duration: "Commercial",
        description: '1004EM001',
        status: 'Active',
        buildings: [
          { id: 201, name: 'Building A', description: '3rd Floor', status: 'Active' },
        ],
      },
      {
        id: 7,
        name: '19a Milverton',
        duration: "Commercial",
        description: '19A001',
        status: 'Active',
        buildings: [
          { id: 201, name: 'Building A', description: '3rd Floor', status: 'Active' },
        ],
      },
    ];

    let locationToShow = 10;

    function renderLocation() {
      sidebarContent.innerHTML = '';
      locations.slice(0, locationToShow).forEach((order) => {
        const content = `
          <div class="location-sidebar_content" data-id="${order.id}">
            <div class="location-name">
              <span>${order.name}</span>
              <h6>${order.duration}</h6>
            </div>
            <div class="location-status">
              <h6>${order.description}</h6>
              <h6>${order.status}</h6>
            </div>
          </div>
        `;
        sidebarContent.insertAdjacentHTML('beforeend', content);
      });

      goodsCount.textContent = `Showing 1 - ${Math.min(locationToShow, locations.length)} of ${locations.length}`;
    }

    function displayItemDetails(id) {
      const location = locations.find((item) => item.id === parseInt(id));

      if (location) {
        locationContent.innerHTML = '';
        buildingContent.style.display = 'flex';
        roomContent.style.display = 'none';
        roomContentDetails.innerHTML = '';

        if (location.buildings && location.buildings.length > 0) {
          location.buildings.forEach((building) => {
            const buildingHTML = `
              <div class="location-sidebar_content" data-id="${building.id}" data-type="building">
                <div class="location-name">
                  <span>${building.name}</span>
                  <h6>${building.status}</h6>
                </div>
                <div class="location-status">
                  <h6>${building.description}</h6>
                </div>
              </div>
            `;
            locationContent.insertAdjacentHTML('beforeend', buildingHTML);
          });
        } else {
          const noContentHTML = `
            <div class="no-content">
              <img src="./assets/img/in-empty-doc-card-icon.svg" alt="No Content" class="no-content-img">
              <h4>Oops!</h4>
              <p>Nothing in Facility/Location</p>
            </div>
          `;
          locationContent.insertAdjacentHTML('beforeend', noContentHTML);
        }
        buildingsCount.textContent = `Showing 1 - ${location.buildings.length} of ${location.buildings.length}`;
      }
    }

    function displayRoomDetails(id) {
      const building = locations.flatMap((loc) => loc.buildings || []).find((b) => b.id === parseInt(id));

      if (building && building.apartment) {
        roomContent.style.display = 'block';
        roomContentDetails.innerHTML = '';

        building.apartment.forEach((apartment) => {
          const apartmentHTML = `
            <div class="location-sidebar_content" data-id="${apartment.id}">
              <div class="location-name">
                <span>${apartment.name}</span>
                <h6>${apartment.status}</h6>
              </div>
              <div class="location-status">
                <h6>${apartment.description}</h6>
              </div>
            </div>
            
          `;
          roomContentDetails.insertAdjacentHTML('beforeend', apartmentHTML);
        });

        roomsCount.textContent = `Showing 1 - ${building.apartment.length} of ${building.apartment.length}`;
      } else {
        roomContentDetails.innerHTML = `
          <div class="no-content">
            <h4>No Rooms Found</h4>
          </div>
        `;
      }
    }

    sidebarContent.addEventListener('click', (event) => {
      const clickedItem = event.target.closest('.location-sidebar_content');
      if (clickedItem) {
        const itemId = clickedItem.dataset.id;
        displayItemDetails(itemId);
      }
    });

    locationContent.addEventListener('click', (event) => {
      const clickedItem = event.target.closest('.location-sidebar_content');
      if (clickedItem && clickedItem.dataset.type === 'building') {
        const buildingId = clickedItem.dataset.id;
        displayRoomDetails(buildingId);
      }
    });

    loadMoreBtn.addEventListener('click', () => {
      locationToShow += 5;
      renderLocation();
    });

    renderLocation();
  });
} catch (error) {
  console.error('Error loading the app:', error);
}


// Javascript Logic for Occupant
try {
  //Toggle Occupant Sidebar

document.addEventListener('DOMContentLoaded', () => {
  const sidebarContent = document.querySelector('.occupant-sidebar_contents');
  const occupantContent = document.querySelector('.occupant-body_content');
  const defaultImage = document.getElementById('default-image')
  const loadMoreBtn = document.getElementById('loadMoreBtn');
  const occupantCount = document.getElementById('occupantCount');

  let occupantSidebar = document.querySelector(".occupant-sidebar");
  let occupantSidebarBtn = document.querySelector(".occupant-sidebarBtn");

  occupantSidebarBtn.addEventListener('click', () => {
    occupantSidebar.classList.toggle('active');
  })


  const occupantDetails = {
    1:{
      name: "Emmanuella Gbinije",
      email: "",
      phone: "",
      client: "Rent Small Small",
      customer: "",
      apartment: "A3-Master Brm",
      contract: "",
      occupiedFrom: "28/05/2020",
      occupiedTo: "27/05/2021",
    },
    2:{
      name: "Emmanuella Gbinije",
      email: "",
      phone: "",
      client: "Rent Small Small",
      customer: "",
      apartment: "A3-Master Brm",
      contract: "",
      occupiedFrom: "28/05/2020",
      occupiedTo: "27/05/2021",
    },
    3:{
      name: "Emmanuella Gbinije",
      email: "",
      phone: "",
      client: "Rent Small Small",
      customer: "",
      apartment: "A3-Master Brm",
      contract: "",
      occupiedFrom: "28/05/2020",
      occupiedTo: "27/05/2021",
    },
    4:{
      name: "Emmanuella Gbinije",
      email: "",
      phone: "",
      client: "Rent Small Small",
      customer: "",
      apartment: "A3-Master Brm",
      contract: "",
      occupiedFrom: "28/05/2020",
      occupiedTo: "27/05/2021",
    },
    5:{
      name: "Emmanuella Gbinije",
      email: "",
      phone: "",
      client: "Rent Small Small",
      customer: "",
      apartment: "A3-Master Brm",
      contract: "",
      occupiedFrom: "28/05/2020",
      occupiedTo: "27/05/2021",
    },
    6:{
      name: "Emmanuella Gbinije",
      email: "",
      phone: "",
      client: "Rent Small Small",
      customer: "",
      apartment: "A3-Master Brm",
      contract: "",
      occupiedFrom: "28/05/2020",
      occupiedTo: "27/05/2021",
    },
    7:{
      name: "Emmanuella Gbinije",
      email: "",
      phone: "",
      client: "Rent Small Small",
      customer: "",
      apartment: "A3-Master Brm",
      contract: "",
      occupiedFrom: "28/05/2020",
      occupiedTo: "27/05/2021",
    },
  };


  const displayItemDetails = (details) => {
    document.getElementById('name').innerText = details.name;
    document.getElementById('email').innerText = details.email;
    document.getElementById('phone').innerText = details.phone;
    document.getElementById('client').innerText = details.client;
    document.getElementById('customer').innerText = details.customer;
    document.getElementById('apartment').innerText = details.apartment;
    document.getElementById('contract').innerText = details.contract;
    document.getElementById('occupiedFrom').innerText = details.occupiedFrom;
    document.getElementById('occupiedTo').innerText = details.occupiedTo;
  }
  
  sidebarContent.addEventListener('click', (event) => {
    const clickedItem = event.target.closest('.occupant-sidebar_content');
    if (clickedItem) {
      const itemId = clickedItem.dataset.id;
      const details = occupantDetails[itemId];
      if (details) {
        defaultImage.style.display = 'none';
        occupantContent.style.display = 'block';
        displayItemDetails(details);
      }
    }
  });

  // Sample data to mimic multiple work order items
  const occupants = [
    { id: 1, name: 'Emmanuel Gbinije', duration: "Rent Small.." },
    { id: 2, name: 'Kelechi', duration: 'Rent Small..' },
    { id: 3, name: 'Tetsoma Akinlonu', duration: 'Rent Small..'},
    { id: 4, name: 'Babajide Abina', duration: 'Rent Small..'},
    { id: 5, name: 'Moyosoreoluwa Jinadu', duration: 'Rent Small..'},
    { id: 6, name: 'Opene-Terry Josiah Ezenwa', duration: 'Rent Small..'},
    { id: 7, name: 'Chieze Ejieh', duration: 'Rent Small..'},
    { id: 8, name: 'Adewoye Damilare', duration: 'Rent Small..'},
    { id: 9, name: 'Nnaemeka Aghaeze', duration: 'Rent Small..'},
    { id: 10, name: 'Bassey Itam', duration: 'Rent Small..'},
    { id: 11, name: 'Obianuju Odum', duration: 'Rent Small..'},
    { id: 12, name: 'Segun Oluwaniyi', duration: 'Rent Small..'},
  ];

  // Number of work orders to show initially
  let occupantToShow = 10;


  // Function to render work orders
  function renderOccupant() {
    // Clear current contents
    sidebarContent.innerHTML = '';
    

    // Render the number of work orders specified by workOrdersToShow
    occupants.slice(0, occupantToShow).forEach(order => {
      const content = `
        <div class="occupant-sidebar_content" data-id="${order.id}">
          <span>${order.name}</span>
          <h6>${order.duration}</h6>
        </div>
      `;
      sidebarContent.insertAdjacentHTML('beforeend', content);
    });
    occupantCount.textContent = `Showing 1 - ${occupantToShow} of ${occupants.length}`;

  
  }

  // Event listener for the "Load More" button
  loadMoreBtn.addEventListener('click', () => {
    // Increase the number of work orders to show by 5
    occupantToShow += 5;

    // If the number of work orders to show exceeds the total, hide the button
    if (occupantToShow >= occupants.length) {
      occupantToShow = occupants.length;
      // loadMoreBtn.style.display = 'none';
    }

    // Render the updated work orders
    renderOccupant();
  });

  // Initial render
  renderOccupant();

})
} catch (error) {
  console.log(error)
}

// Javascript Logic for Bulk Notification
try {
  //Toggle Occupant Sidebar

document.addEventListener('DOMContentLoaded', () => {
  const sidebarContent = document.querySelector('.bulkNotify-sidebar_contents');
  const bulkNotifyContent = document.querySelector('.bulkNotify-body_content');
  const defaultImage = document.getElementById('default-image')
  const loadMoreBtn = document.getElementById('loadMoreBtn');
  const bulkNotifyCount = document.getElementById('bulkNotifyCount');

  let bulkNotifySidebar = document.querySelector(".bulkNotify-sidebar");
  let bulkNotifySidebarBtn = document.querySelector(".bulkNotify-sidebarBtn");

  bulkNotifySidebarBtn.addEventListener('click', () => {
    bulkNotifySidebar.classList.toggle('active');
  })


  const bulkNotifyDetails = {
    1:{
      number: "0000033",
      type: "Item",
      title: "Cleaning Consumables for March 2022",
      submit: "25/03/2022",
      facility: "MTN COTE D'IVOIRE",
      currency: "XOF",
      deadline: "27/03/2022 08:52 AM",
      status: "Submitted",
    },

    2:{
      number: "0000033",
      type: "Item",
      title: "Cleaning Consumables for March 2022",
      submit: "25/03/2022",
      facility: "MTN COTE D'IVOIRE",
      currency: "XOF",
      deadline: "27/03/2022 08:52 AM",
      status: "Submitted",
    },

    3:{
      number: "0000033",
      type: "Item",
      title: "Cleaning Consumables for March 2022",
      submit: "25/03/2022",
      facility: "MTN COTE D'IVOIRE",
      currency: "XOF",
      deadline: "27/03/2022 08:52 AM",
      status: "Submitted",
    },

    4:{
      number: "0000033",
      type: "Item",
      title: "Cleaning Consumables for March 2022",
      submit: "25/03/2022",
      facility: "MTN COTE D'IVOIRE",
      currency: "XOF",
      deadline: "27/03/2022 08:52 AM",
      status: "Submitted",
    },

    5:{
      number: "0000033",
      type: "Item",
      title: "Cleaning Consumables for March 2022",
      submit: "25/03/2022",
      facility: "MTN COTE D'IVOIRE",
      currency: "XOF",
      deadline: "27/03/2022 08:52 AM",
      status: "Submitted",
    },

    6:{
      number: "0000033",
      type: "Item",
      title: "Cleaning Consumables for March 2022",
      submit: "25/03/2022",
      facility: "MTN COTE D'IVOIRE",
      currency: "XOF",
      deadline: "27/03/2022 08:52 AM",
      status: "Submitted",
    },

    7:{
      number: "0000033",
      type: "Item",
      title: "Cleaning Consumables for March 2022",
      submit: "25/03/2022",
      facility: "MTN COTE D'IVOIRE",
      currency: "XOF",
      deadline: "27/03/2022 08:52 AM",
      status: "Submitted",
    },

    8:{
      number: "0000033",
      type: "Item",
      title: "Cleaning Consumables for March 2022",
      submit: "25/03/2022",
      facility: "MTN COTE D'IVOIRE",
      currency: "XOF",
      deadline: "27/03/2022 08:52 AM",
      status: "Submitted",
    },

    9:{
      number: "0000033",
      type: "Item",
      title: "Cleaning Consumables for March 2022",
      submit: "25/03/2022",
      facility: "MTN COTE D'IVOIRE",
      currency: "XOF",
      deadline: "27/03/2022 08:52 AM",
      status: "Submitted",
    },

    10:{
      number: "0000033",
      type: "Item",
      title: "Cleaning Consumables for March 2022",
      submit: "25/03/2022",
      facility: "MTN COTE D'IVOIRE",
      currency: "XOF",
      deadline: "27/03/2022 08:52 AM",
      status: "Submitted",
    },

    11:{
      number: "0000033",
      type: "Item",
      title: "Cleaning Consumables for March 2022",
      submit: "25/03/2022",
      facility: "MTN COTE D'IVOIRE",
      currency: "XOF",
      deadline: "27/03/2022 08:52 AM",
      status: "Submitted",
    },
    
  };


  const displayItemDetails = (details) => {
    document.getElementById('number').innerText = details.number;
    document.getElementById('type').innerText = details.type;
    document.getElementById('title').innerText = details.title;
    document.getElementById('submit-date').innerText = details.ssubmit;
    document.getElementById('facility').innerText = details.facility;
    document.getElementById('currency').innerText = details.currency;
    document.getElementById('deadline-date').innerText = details.deadline;
    document.getElementById('status').innerText = details.status;
  }
  
  sidebarContent.addEventListener('click', (event) => {
    const clickedItem = event.target.closest('.bulkNotify-sidebar_content');
    if (clickedItem) {
      const itemId = clickedItem.dataset.id;
      const details = bulkNotifyDetails[itemId];
      if (details) {
        defaultImage.style.display = 'none';
        bulkNotifyContent.style.display = 'block';
        displayItemDetails(details);
      }
    }
  });


})
} catch (error) {
  console.log(error)
}

// Javascript Logic for Facility Invoice

try {
  //Toggle Occupant Sidebar

document.addEventListener('DOMContentLoaded', () => {
  const sidebarContent = document.querySelector('.invoice-sidebar_contents');
  const invoiceContent = document.querySelector('.invoice-body_content');
  const defaultImage = document.getElementById('default-image')
  const loadMoreBtn = document.getElementById('loadMoreBtn');
  const invoiceCount = document.getElementById('invoiceCount');

  let invoiceSidebar = document.querySelector(".invoice-sidebar");
  let invoiceSidebarBtn = document.querySelector(".invoice-sidebarBtn");

  invoiceSidebarBtn.addEventListener('click', () => {
    invoiceSidebar.classList.toggle('active');
  })


  const invoiceDetails = {
    1:{
      number: "0000033",
      type: "Item",
      title: "Cleaning Consumables for March 2022",
      submit: "25/03/2022",
      facility: "MTN COTE D'IVOIRE",
      currency: "XOF",
      deadline: "27/03/2022 08:52 AM",
      status: "Submitted",
    },

    2:{
      number: "0000033",
      type: "Item",
      title: "Cleaning Consumables for March 2022",
      submit: "25/03/2022",
      facility: "MTN COTE D'IVOIRE",
      currency: "XOF",
      deadline: "27/03/2022 08:52 AM",
      status: "Submitted",
    },

    3:{
      number: "0000033",
      type: "Item",
      title: "Cleaning Consumables for March 2022",
      submit: "25/03/2022",
      facility: "MTN COTE D'IVOIRE",
      currency: "XOF",
      deadline: "27/03/2022 08:52 AM",
      status: "Submitted",
    },

    4:{
      number: "0000033",
      type: "Item",
      title: "Cleaning Consumables for March 2022",
      submit: "25/03/2022",
      facility: "MTN COTE D'IVOIRE",
      currency: "XOF",
      deadline: "27/03/2022 08:52 AM",
      status: "Submitted",
    },

    5:{
      number: "0000033",
      type: "Item",
      title: "Cleaning Consumables for March 2022",
      submit: "25/03/2022",
      facility: "MTN COTE D'IVOIRE",
      currency: "XOF",
      deadline: "27/03/2022 08:52 AM",
      status: "Submitted",
    },

    6:{
      number: "0000033",
      type: "Item",
      title: "Cleaning Consumables for March 2022",
      submit: "25/03/2022",
      facility: "MTN COTE D'IVOIRE",
      currency: "XOF",
      deadline: "27/03/2022 08:52 AM",
      status: "Submitted",
    },

    7:{
      number: "0000033",
      type: "Item",
      title: "Cleaning Consumables for March 2022",
      submit: "25/03/2022",
      facility: "MTN COTE D'IVOIRE",
      currency: "XOF",
      deadline: "27/03/2022 08:52 AM",
      status: "Submitted",
    },

    8:{
      number: "0000033",
      type: "Item",
      title: "Cleaning Consumables for March 2022",
      submit: "25/03/2022",
      facility: "MTN COTE D'IVOIRE",
      currency: "XOF",
      deadline: "27/03/2022 08:52 AM",
      status: "Submitted",
    },

    9:{
      number: "0000033",
      type: "Item",
      title: "Cleaning Consumables for March 2022",
      submit: "25/03/2022",
      facility: "MTN COTE D'IVOIRE",
      currency: "XOF",
      deadline: "27/03/2022 08:52 AM",
      status: "Submitted",
    },

    10:{
      number: "0000033",
      type: "Item",
      title: "Cleaning Consumables for March 2022",
      submit: "25/03/2022",
      facility: "MTN COTE D'IVOIRE",
      currency: "XOF",
      deadline: "27/03/2022 08:52 AM",
      status: "Submitted",
    },

    11:{
      number: "0000033",
      type: "Item",
      title: "Cleaning Consumables for March 2022",
      submit: "25/03/2022",
      facility: "MTN COTE D'IVOIRE",
      currency: "XOF",
      deadline: "27/03/2022 08:52 AM",
      status: "Submitted",
    },
    
  };


  const displayItemDetails = (details) => {
    document.getElementById('number').innerText = details.number;
    document.getElementById('type').innerText = details.type;
    document.getElementById('title').innerText = details.title;
    document.getElementById('submit-date').innerText = details.ssubmit;
    document.getElementById('facility').innerText = details.facility;
    document.getElementById('currency').innerText = details.currency;
    document.getElementById('deadline-date').innerText = details.deadline;
    document.getElementById('status').innerText = details.status;
  }
  
  sidebarContent.addEventListener('click', (event) => {
    const clickedItem = event.target.closest('.invoice-sidebar_content');
    if (clickedItem) {
      const itemId = clickedItem.dataset.id;
      const details = invoiceDetails[itemId];
      if (details) {
        defaultImage.style.display = 'none';
        invoiceContent.style.display = 'block';
        displayItemDetails(details);
      }
    }
  });


})
} catch (error) {
  console.log(error)
}


// Javascript Logic for Reference Section
// Javascript Logic for User Management

// try {
//   //Toggle User Sidebar
// document.addEventListener('DOMContentLoaded', () => {
//   const sidebarContent = document.querySelector('.user-sidebar_contents');
//   const defaultImage = document.getElementById('default-image');
//   const userContent = document.querySelector('.user-body_content');
//   const loadMoreBtn = document.getElementById('loadMoreBtn');
//   let userSidebar = document.querySelector(".user-sidebar");
//   let userSidebarBtn = document.querySelector(".user-sidebarBtn");
//   const userCount = document.getElementById('userCount');

//   userSidebarBtn.addEventListener('click', () => {
//     userSidebar.classList.toggle('active');
//   })

//   const userDetails = {
//     1:{
//       firstName: 'Aanuoluwa',
//       lastName: 'Adekola',
//       email: 'Aanuoluwa.Adekola@alphamead.com',
//       phoneNumber: '08100820679',
//       designation: 'Planning Officer',
//       gender: 'Male',
//       nationality: 'Nigerian',
//       status: 'Active'
//     },
//     2:{
//       firstName: 'Aanuoluwa',
//       lastName: 'Adekola',
//       email: 'Aanuoluwa.Adekola@alphamead.com',
//       phoneNumber: '08100820679',
//       designation: 'Planning Officer',
//       gender: 'Male',
//       nationality: 'Nigerian',
//       status: 'Active'
//     },
//     3:{
//       firstName: 'Aanuoluwa',
//       lastName: 'Adekola',
//       email: 'Aanuoluwa.Adekola@alphamead.com',
//       phoneNumber: '08100820679',
//       designation: 'Planning Officer',
//       gender: 'Male',
//       nationality: 'Nigerian',
//       status: 'Active'
//     },
//     4:{
//       firstName: 'Aanuoluwa',
//       lastName: 'Adekola',
//       email: 'Aanuoluwa.Adekola@alphamead.com',
//       phoneNumber: '08100820679',
//       designation: 'Planning Officer',
//       gender: 'Male',
//       nationality: 'Nigerian',
//       status: 'Active'
//     },
//     5:{
//       firstName: 'Aanuoluwa',
//       lastName: 'Adekola',
//       email: 'Aanuoluwa.Adekola@alphamead.com',
//       phoneNumber: '08100820679',
//       designation: 'Planning Officer',
//       gender: 'Male',
//       nationality: 'Nigerian',
//       status: 'Active'
//     },
//   };

  
//   const displayItemDetails = (details) => {
//     document.getElementById('first-name').innerText = details.firstName;
//     document.getElementById('last-name').innerText = details.lastName;
//     document.getElementById('user-email').innerText = details.email;
//     document.getElementById('user-phone').innerText = details.phoneNumber;
//     document.getElementById('user-designation').innerText = details.designation;
//     document.getElementById('gender').innerText = details.gender;
//     document.getElementById('nationality').innerText = details.nationality;
//     document.getElementById('user-status').innerText = details.status;
//   }
  
//   sidebarContent.addEventListener('click', (event) => {
//     const clickedItem = event.target.closest('.user-sidebar_content');
//     if (clickedItem) {
//       const itemId = clickedItem.dataset.id;
//       const details = userDetails[itemId];
//       if (details) {
//         defaultImage.style.display = 'none';
//         userContent.style.display = 'block';
//         displayItemDetails(details);
//       }
//     }
//   });

//   // Sample data to mimic multiple user items
//   const users = [
//     { id: 1, name: 'Aanuoluwapo Adekola', imgUrl: "./assets/img/In-user-icon.svg", status: 'Active' },
//     { id: 2, name: 'Aanuoluwapo Adekola', imgUrl: "./assets/img/In-user-icon.svg", status: 'Active' },
//     { id: 3, name: 'Aanuoluwapo Adekola', imgUrl: "./assets/img/In-user-icon.svg", status: 'Active' },
//     { id: 4, name: 'Aanuoluwapo Adekola', imgUrl: "./assets/img/In-user-icon.svg", status: 'Active' },
//     { id: 5, name: 'Aanuoluwapo Adekola', imgUrl: "./assets/img/In-user-icon.svg", status: 'Active' },
    
//   ];

//   // Number of users to show initially
//   let userToShow = 5;

//   // Function to render users
//   function renderUser() {
//     // Clear current contents
//     sidebarContent.innerHTML = '';
    
//     // Render the number of users specified by userToShow
//     users.slice(0, userToShow).forEach(order => {
//       const content = `
//         <div class="user-sidebar_content" data-id="${order.id}">
//           <div class="user-sidebar_profile">
//             <img src=${order.imgUrl} alt="">
//             <div class="user-sidebar_name">
//               <span>${order.name}</span>
//               <p>${order.name}...</p>
//             </div>
//           </div>
//           <h6>${order.status}</h6>
//         </div>
//       `;
//       sidebarContent.insertAdjacentHTML('beforeend', content);
//     });
//     userCount.textContent = `Showing 1 - ${userToShow} of ${users.length}`;
//   }

//   // Event listener for the "Load More" button
//   loadMoreBtn.addEventListener('click', () => {
//     // Increase the number of users to show by 5
//     userToShow += 5;

//     // If the number of users to show exceeds the total, hide the button
//     if (userToShow >= users.length) {
//       userToShow = users.length;
//       // loadMoreBtn.style.display = 'none';
//     }

//     // Render the updated users
//     renderUser();
//   });

//   // Initial render
//   renderUser();
  
// })
// } catch (error) {
//   console.log(error)
// }

// Javascript Logic for Personnel
try {
  //Toggle Personnel Sidebar
document.addEventListener('DOMContentLoaded', () => {
  const sidebarContent = document.querySelector('.personnel-sidebar_contents');
  const personnelContent = document.querySelector('.personnel-body_content');
  const defaultImage = document.getElementById('default-image');
  let personnelSidebar = document.querySelector('.personnel-sidebar');
  let personnelSidebarBtn = document.querySelector('.personnel-sidebarBtn');
  const loadMoreBtn = document.getElementById('loadMoreBtn');
  const personnelCount = document.getElementById('personnelCount');
  let addButtonImage = document.querySelector('.uploadImage');  // Upload image button
  let fileInputImage = document.getElementById('personal-image-input');  // File input for image

  let addButtonDoc = document.querySelector('.personnel-modal_add button');  // Add document button
  let fileInputDoc = document.getElementById('document-input');  // File input for document

  personnelSidebarBtn.addEventListener('click', () => {
    personnelSidebar.classList.toggle('active');
  })


  const personnelDetails = {
    1:{
      staffNumber: '0113',
      firstName: 'Aji',
      middleName: '',
      lastName: 'Abana',
      facility: 'Yes',
    },
    2:{
      staffNumber: '',
      firstName: 'Peter',
      middleName: '',
      lastName: 'Abang',
      facility: 'Yes',
    },
    3:{
      staffNumber: '151266',
      firstName: 'Idris',
      middleName: 'Olawale',
      lastName: 'Abass',
      facility: 'Yes',
    },
    4:{
      staffNumber: '0109',
      firstName: 'Deborah',
      middleName: '',
      lastName: 'Abdul',
      facility: 'Yes',
    },
    5:{
      staffNumber: '191882',
      firstName: 'Peter',
      middleName: 'Adeola',
      lastName: 'Abdul',
      facility: 'Yes',
    },
  };

  
  const displayItemDetails = (details) => {
    document.getElementById('first-name').innerText = details.firstName;
    document.getElementById('last-name').innerText = details.lastName;
    document.getElementById('staff-number').innerText = details.staffNumber;
    document.getElementById('middle-name').innerText = details.middleName;
    document.getElementById('personnel-facility').innerText = details.facility;
  }
  
  sidebarContent.addEventListener('click', (event) => {
    const clickedItem = event.target.closest('.personnel-sidebar_content');
    if (clickedItem) {
      const itemId = clickedItem.dataset.id;
      const details = personnelDetails[itemId];
      if (details) {
        defaultImage.style.display = 'none';
        personnelContent.style.display = 'block';
        displayItemDetails(details);
      }
    }
  });

  const personnels = [
    { id: 1, name: 'Aji Abana', number: "0113", status: 'Active' },
    { id: 2, name: 'Peter Abang', number: '', status: 'Inactive' },
    { id: 3, name: 'Idris Olawale Abass', number: '151266', status: 'Active' },
    { id: 4, name: 'Deborah Abdul', number: '0109', status: 'Active' },
    { id: 5, name: 'Peter Adeola Abdul', number: '191882', status: 'Active' },
  ];

  // Number of work orders to show initially
  let personnelToShow = 10;

  // Function to render work orders
  function renderPersonnel() {
    // Clear current contents
    sidebarContent.innerHTML = '';
    

    // Render the number of work orders specified by workOrdersToShow
    personnels.slice(0, personnelToShow).forEach(order => {
      const content = `
        <div class="personnel-sidebar_content" data-id="${order.id}">
          <div class="personnel-name">
            <span>${order.name}</span>
            <h6>${order.status}</h6>
          </div>
          <div class="personnel-number">
            <h6>${order.number}</h6>
            <h6></h6>
          </div>
        </div>
      `;
      sidebarContent.insertAdjacentHTML('beforeend', content);
    });
    personnelCount.textContent = `Showing 1 - ${personnelToShow} of ${personnels.length}`;
  }

  // Event listener for the "Load More" button
  loadMoreBtn.addEventListener('click', () => {
    // Increase the number of work orders to show by 5
    personnelToShow += 5;

    // If the number of work orders to show exceeds the total, hide the button
    if (personnelToShow >= personnels.length) {
      personnelToShow = personnels.length;
      // loadMoreBtn.style.display = 'none';
    }

    // Render the updated work orders
  });

  // Initial render
  renderPersonnel();

  //Javascript for the Add Button Functionality

  addButtonImage.addEventListener('click', () => {
    fileInputImage.click(); // Simulate file input click
  });

  addButtonDoc.addEventListener('click', () => {
    fileInputDoc.click();  // Trigger the file input for document
  });


  fileInputImage.addEventListener('change', (event) => {
    const file = event.target.files[0];
    if (file) {
      console.log('Selected image file:', file.name);
      alert('Selected image file: ' + file.name);  // For demonstration purposes
    }
  });

  // File input change event for document
  fileInputDoc.addEventListener('change', (event) => {
    const file = event.target.files[0];
    if (file) {
      console.log('Selected document file:', file.name);
      alert('Selected document file: ' + file.name);  // For demonstration purposes
    }
  });
  
  
})
} catch (error) {
  console.log(error)
}

// Javascript Logic for Vendor
try {
  //Toggle Vendor Sidebar

document.addEventListener('DOMContentLoaded', () => {
  const sidebarContent = document.querySelector('.vendor-sidebar_contents');
  const defaultImage = document.getElementById('default-image');
  const vendorContent = document.querySelector('.vendor-body_content');
  let vendorSidebar = document.querySelector(".vendor-sidebar");
  let vendorSidebarBtn = document.querySelector(".vendor-sidebarBtn");
  const loadMoreBtn = document.getElementById('loadMoreBtn');
  const vendorsCount = document.getElementById('vendorCount');
  let vendorAddBtn = document.querySelector('.vendor-modal_add')
  let vendorContactDetails = document.querySelector('.vendor-modal_contact-details')
  let vendorRemoveDetails = document.querySelector('.vendor-remove-details');
  let vendorAddFile = document.querySelector('.vendor-modal_add-file');
  let vendorFileDetails = document.querySelector('.vendor-modal_file-details')
  let vendorRemoveFile = document.querySelector('.vendor-remove-file-details')
  let vendorAddContract = document.querySelector('.vendor-modal_add-contract');
  let vendorContractDetails = document.querySelector('.vendor-modal_contract-details')
  let vendorRemoveContract = document.querySelector('.vendor-remove-contract-details')


  vendorSidebarBtn.addEventListener('click', () => {
    vendorSidebar.classList.toggle('active');
  })


  const vendorDetails = {
    1:{
      type: 'Company',
      code: 'ALP008',
      name: 'Alpha Mead Facilities Management Services',
      addVat: 'No',
      address: '6 Mobolaji Johnson Avenue, Ikoyi',
      status: 'Active',
    },
    2:{
      type: 'Company',
      code: 'ALP008',
      name: 'Alpha Mead Facilities Management Services',
      addVat: 'No',
      address: '6 Mobolaji Johnson Avenue, Ikoyi',
      status: 'Active',
    },
    3:{
      type: 'Company',
      code: 'ALP008',
      name: 'Alpha Mead Facilities Management Services',
      addVat: 'N',
      address: '6 Mobolaji Johnson Avenue, Ikoyi',
      status: 'Active',
    },
    4:{
      type: 'Company',
      code: 'ALP008',
      name: 'Alpha Mead Facilities Management Services',
      addVat: 'N',
      address: '6 Mobolaji Johnson Avenue, Ikoyi',
      status: 'Active',
    },
    5:{
      type: 'Company',
      code: 'ALP008',
      name: 'Alpha Mead Facilities Management Services',
      addVat: 'N',
      address: '6 Mobolaji Johnson Avenue, Ikoyi',
      status: 'Active',
    },
  };

  
  const displayItemDetails = (details) => {
    document.getElementById('type').innerText = details.type;
    document.getElementById('code').innerText = details.code;
    document.getElementById('type-name').innerText = details.name;
    document.getElementById('add-vat').innerText = details.addVat;
    document.getElementById('address').innerText = details.address;
    document.getElementById('status').innerText = details.status;
  }

  sidebarContent.addEventListener('click', (event) => {
    const clickedItem = event.target.closest('.vendor-sidebar_content');
    if (clickedItem) {
      const itemId = clickedItem.dataset.id;
      const details = vendorDetails[itemId];
      if (details) {
        defaultImage.style.display = 'none';
        vendorContent.style.display = 'block';
        displayItemDetails(details);
      }
    }
  });

  const vendors = [
    { id: 1, name: 'Alpha Mead Facilities Management Services', company: "Company", number: 'ALP008', status: 'Active' },
    { id: 2, name: 'CHARTEX AUTO', company: "Company", number: 'CHA001', status: 'Active' },
    { id: 3, name: 'Comstream Nigeria Limited', company: "Company", number: 'COM001', status: 'Active' },
    { id: 4, name: 'Ikenna Daniel Engineering', company: "Company", number: 'IKE001', status: 'Active' },
    { id: 5, name: 'Instablog9ja', company: "Company", number: 'INS001', status: 'Active' },
    
  ];

  // Number of work orders to show initially
  let vendorToShow = 10;

  // Function to render work orders
  function renderVendor() {
    // Clear current contents
    sidebarContent.innerHTML = '';
    

    // Render the number of work orders specified by workOrdersToShow
    vendors.slice(0, vendorToShow).forEach(order => {
      const content = `
        <div class="vendor-sidebar_content" data-id="${order.id}">
          <div class="vendor-name">
            <span>${order.name}</span>
            <h6>${order.company}</h6>
          </div>
          <div class="vendor-status">
            <h6>${order.number}</h6>
            <h6>${order.status}</h6>
          </div>
        </div>
      `;
      sidebarContent.insertAdjacentHTML('beforeend', content);
    });
    vendorsCount.textContent = `Showing 1 - ${vendorToShow} of ${vendors.length}`;
  }

  // Event listener for the "Load More" button
  loadMoreBtn.addEventListener('click', () => {
    // Increase the number of work orders to show by 5
    vendorToShow += 5;

    // If the number of work orders to show exceeds the total, hide the button
    if (vendorToShow >= vendors.length) {
      vendorToShow = vendors.length;
      // loadMoreBtn.style.display = 'none';
    }

    // Render the updated work orders
  });

  // Initial render
  renderVendor();

  vendorAddBtn.addEventListener('click', () => {
    vendorContactDetails.style.display = "block"
    vendorAddBtn.style.display = "none"
  })

  vendorRemoveDetails.addEventListener('click', () => {
    vendorContactDetails.style.display = "none"
    vendorAddBtn.style.display = "block"
  })

  vendorAddFile.addEventListener('click', () => {
    vendorFileDetails.style.display = "block"
    vendorAddFile.style.display = "none"
  })

  vendorRemoveFile.addEventListener('click', () => {
    vendorFileDetails.style.display = "none"
    vendorAddFile.style.display = "block"
  })

  vendorAddContract.addEventListener('click', () => {
    vendorContractDetails.style.display = "block"
    vendorAddContract.style.display = "none"
  })

  vendorRemoveContract.addEventListener('click', () => {
    vendorContractDetails.style.display = "none"
    vendorAddContract.style.display = "block"
  })
  
  
})
} catch (error) {
 console.log(error) 
}

// Javascript Logic for Client
try {
  //Toggle Client Sidebar

document.addEventListener('DOMContentLoaded', () => {
  const sidebarContent = document.querySelector('.client-sidebar_contents');
  const defaultImage = document.getElementById('default-image');
  const clientsContent = document.querySelector('');
  let clientSidebar = document.querySelector(".client-sidebar");
  let clientSidebarBtn = document.querySelector(".client-sidebarBtn");
  const loadMoreBtn = document.getElementById('loadMoreBtn');
  const clientCount = document.getElementById('clientCount');
  let clientAddBtn = document.querySelector('.client-modal_add')
  let clientContactDetails = document.querySelector('.client-modal_contact-details')
  let clientRemoveDetails = document.querySelector('.client-remove-details');

  clientSidebarBtn.addEventListener('click', () => {
    clientSidebar.classList.toggle('active');
  })


  const clientDetails = {
    1:{
      type: 'Company',
      code: 'AMF',
      name: 'AMFacilities',
      email: 'COPS@ALPHAMEAD.COM',
      phone: '07019999219',
      status: 'Active',
    },
    2:{
      type: 'Company',
      code: 'AMF',
      name: 'AMFacilities',
      email: 'COPS@ALPHAMEAD.COM',
      phone: '07019999219',
      status: 'Active',
    },
    3:{
      type: 'Company',
      code: 'AMF',
      name: 'AMFacilities',
      email: 'COPS@ALPHAMEAD.COM',
      phone: '07019999219',
      status: 'Active',
    },
    4:{
      type: 'Company',
      code: 'AMF',
      name: 'AMFacilities',
      email: 'COPS@ALPHAMEAD.COM',
      phone: '07019999219',
      status: 'Active',
    },
    5:{
      type: 'Company',
      code: 'AMF',
      name: 'AMFacilities',
      email: 'COPS@ALPHAMEAD.COM',
      phone: '07019999219',
      status: 'Active',
    },
      
  };

  
  const displayItemDetails = (details) => {
    document.getElementById('type').innerText = details.type;
    document.getElementById('code').innerText = details.code;
    document.getElementById('type-name').innerText = details.name;
    document.getElementById('type-email').innerText = details.email;
    document.getElementById('type-phone').innerText = details.phone;
    document.getElementById('status').innerText = details.status;
  }

  sidebarContent.addEventListener('click', (event) => {
    const clickedItem = event.target.closest('.client-sidebar_content');
    if (clickedItem) {
      const itemId = clickedItem.dataset.id;
      const details = clientDetails[itemId];
      if (details) {
        defaultImage.style.display = 'none';
        clientsContent.style.display = 'block';
        displayItemDetails(details);
      }
    }
  });

  const clients = [
    { id: 1, name: 'AMFacilities', company: "Company", number: 'AMF', status: 'Active' },
    { id: 2, name: 'Central ops', company: "Company", number: 'COPS', status: 'Active' },
    { id: 3, name: 'NESTLE(H.O) NIG', company: "Company", number: 'NESTLE NIG', status: 'Active' },
    { id: 4, name: 'Rent Small Small', company: "Individual", number: '', status: 'Active' },
    { id: 5, name: 'Rent4Less', company: "Individual", number: '', status: 'Active' },
    
  ];

  // Number of work orders to show initially
  let clientToShow = 10;

  // Function to render work orders
  function renderClient() {
    // Clear current contents
    sidebarContent.innerHTML = '';
    

    // Render the number of work orders specified by workOrdersToShow
    clients.slice(0, clientToShow).forEach(order => {
      const content = `
        <div class="client-sidebar_content" data-id="${order.id}">
          <div class="client-name">
            <span>${order.name}</span>
            <h6>${order.company}</h6>
          </div>
          <div class="vendor-status">
            <h6>${order.number}</h6>
            <h6>${order.status}</h6>
          </div>
        </div>
      `;
      sidebarContent.insertAdjacentHTML('beforeend', content);
    });
    clientCount.textContent = `Showing 1 - ${clientToShow} of ${clients.length}`;
  }

  // Event listener for the "Load More" button
  loadMoreBtn.addEventListener('click', () => {
    // Increase the number of work orders to show by 5
    clientToShow += 5;

    // If the number of work orders to show exceeds the total, hide the button
    if (clientToShow >= clients.length) {
      clientToShow = clients.length;
      // loadMoreBtn.style.display = 'none';
    }

    // Render the updated work orders
  });

  // Initial render
  renderClient();

  clientAddBtn.addEventListener('click', () => {
    clientContactDetails.style.display = "block"
    clientAddBtn.style.display = "none"
  })
  
  clientRemoveDetails.addEventListener('click', () => {
    clientContactDetails.style.display = "none"
    clientAddBtn.style.display = "block"
  })
  
})
} catch (error) {
  console.log(error)
}

// Javascript Logic for Department
try {
  //Toggle Department Sidebar
let departmentSidebar = document.querySelector(".department-sidebar");
let departmentSidebarBtn = document.querySelector(".department-sidebarBtn");

departmentSidebarBtn.addEventListener('click', () => {
    departmentSidebar.classList.toggle('active');
})

document.addEventListener('DOMContentLoaded', () => {
  const departments = document.querySelectorAll('.department-sidebar_content');
  const defaultImage = document.getElementById('default-image');
  const departmentContent = document.querySelector('');



  const departmentDetails = {
      1:{
          code: 'AMG 1',
          name: 'ADMIN',
          status: 'Active',
      },
      2:{
          code: 'AMF',
          name: 'AMFacilities',
          status: 'Active',
      },
      3:{
          code: 'AMF',
          name: 'AMFacilities',
          status: 'Active',
      },
      4:{
          code: 'AMF',
          name: 'AMFacilities',
          status: 'Active',
      },
      5:{
          code: 'AMF',
          name: 'AMFacilities',
          status: 'Active',
      },
      
  };

  
  const displayItemDetails = (details) => {
      document.getElementById('code').innerText = details.code;
      document.getElementById('type-name').innerText = details.name;
      document.getElementById('status').innerText = details.status;
  }
  
  departments.forEach(item => {
      item.addEventListener('click', () => {
          const itemId = item.dataset.id;
          const details = departmentDetails[itemId];
  
          if (details) {
              defaultImage.style.display = 'none';
              departmentContent.style.display = 'block';
              displayItemDetails(details)
          }
      })
  });
})
} catch (error) {
  console.log(error)
}

// Javascript Logic for Bank Account
try {
  //Toggle Bank Sidebar
let bankSidebar = document.querySelector(".bank-sidebar");
let bankSidebarBtn = document.querySelector(".bank-sidebarBtn");

bankSidebarBtn.addEventListener('click', () => {
    bankSidebar.classList.toggle('active');
})

document.addEventListener('DOMContentLoaded', () => {
  const banks = document.querySelectorAll('.bank-sidebar_content');
  const defaultImage = document.getElementById('default-image');
  const bankContent = document.querySelector('.bank-body_content');



  const bankDetails = {
      1:{
          bank: 'Guaranty Trust Bank',
          accountName: 'Alpha Mead Real Estate Partners',
          accountNumber: '0464807415',
          currency: 'NGN',
          status: 'Active',
          address: 'Southern View & Milverton'
      },
      2:{
          bank: 'First City Monument Bank',
          accountName: 'Alpha Mead Real Estate Partners',
          accountNumber: '6043987015',
          currency: 'NGN',
          status: 'Active',
          address: 'Lekki Pearl & Lekki Phase 1'
      },
      
      
  };

  
  const displayItemDetails = (details) => {
      document.getElementById('bank').innerText = details.bank;
      document.getElementById('account-name').innerText = details.accountName;
      document.getElementById('account-number').innerText = details.accountNumber;
      document.getElementById('currency').innerText = details.currency;
      document.getElementById('address').innerText = details.address;
      document.getElementById('type-status').innerText = details.status;
  }
  
  banks.forEach(item => {
      item.addEventListener('click', () => {
          const itemId = item.dataset.id;
          const details = bankDetails[itemId];
  
          if (details) {
              defaultImage.style.display = 'none';
              bankContent.style.display = 'block';
              displayItemDetails(details)
          }
      })
  });
})
} catch (error) {
 console.log(error) 
}

// Javascript Logic for Settings

// Javascript Logic for Alert Settings
try {
  //Toggle Alert Sidebar
let alertSidebar = document.querySelector(".alert-sidebar");
let alertSidebarBtn = document.querySelector(".alert-sidebarBtn");

alertSidebarBtn.addEventListener('click', () => {
    alertSidebar.classList.toggle('active');
})

document.addEventListener('DOMContentLoaded', () => {
  const alerts = document.querySelectorAll('.alert-sidebar_content');
  const defaultImage = document.getElementById('default-image');
  const alertContent = document.querySelector('.alert-body_content');



  const alertDetails = {
      1:{
          type: 'Facility/Location',
          location: '1 Moore Road',
      },
      2:{
          type: 'Facility/Location',
          location: '1 Moore Road',
      },
      3:{
          type: 'Facility/Location',
          location: '1 Moore Road',
      },
      4:{
          type: 'Facility/Location',
          location: '1 Moore Road',
      },
      5:{
          type: 'Facility/Location',
          location: '1 Moore Road',
      },
      
      
  };

  
  const displayItemDetails = (details) => {
      document.getElementById('type').innerText = details.type;
      document.getElementById('location').innerText = details.location;
  }
  
  alerts.forEach(item => {
      item.addEventListener('click', () => {
          const itemId = item.dataset.id;
          const details = alertDetails[itemId];
  
          if (details) {
              defaultImage.style.display = 'none';
              alertContent.style.display = 'block';
              displayItemDetails(details)
          }
      })
  });
})
} catch (error) {
  console.log(error)
}

// Javascript Logic for Escalation Settings
try {
  //Toggle Escalation Sidebar
let escalationSidebar = document.querySelector(".escalation-sidebar");
let escalationSidebarBtn = document.querySelector(".escalation-sidebarBtn");

escalationSidebarBtn.addEventListener('click', () => {
    escalationSidebar.classList.toggle('active');
})

document.addEventListener('DOMContentLoaded', () => {
  const escalations = document.querySelectorAll('.escalation-sidebar_content');
  const defaultImage = document.getElementById('default-image');
  const escalationContent = document.querySelector('.escalation-body_content');



  const escalationDetails = {
      1:{
          number: '0000006',
          type: 'Use',
          category: 'Category 1',
          date: new Date(),
          department: 'Central Operations',
          status: 'Submitted',
          location: 'New Head Office'
      },
  
      2:{
          number: '0000005',
          type: 'Use',
          category: 'Category 2',
          date: new Date(),
          department: 'Central Operations',
          status: 'Submitted',
          location: 'New Head Office'
      }
  };

  const displayItemDetails = (details) => {
      document.getElementById('number').innerText = details.number
      document.getElementById('type').innerText = details.type;
      document.getElementById('category').innerText = details.category;
      document.getElementById('date').innerText = details.formattedDate;
      document.getElementById('required-date').innerText = details.formattedDate;
      document.getElementById('item-department').innerText = details.department;
      document.getElementById('item-status').innerText = details.status;
      document.getElementById('location').innerText = details.location;
      // document.querySelectorAll('.item-date').innerText = details.formattedDate;
  }
  
  escalations.forEach(item => {
      item.addEventListener('click', () => {
          const itemId = item.dataset.id;
          const details = escalationDetails[itemId];
  
          if (details) {
              defaultImage.style.display = 'none';
              escalationContent.style.display = 'block';
              displayItemDetails(details)
          }
      })
  });
})
} catch (error) {
  console.log(error)
}

// Javascript Logic for SLA Settings
try {
  //Toggle SLA Sidebar
let slaSidebar = document.querySelector(".sla-sidebar");
let slaSidebarBtn = document.querySelector(".sla-sidebarBtn");

slaSidebarBtn.addEventListener('click', () => {
  slaSidebar.classList.toggle('active');
})

document.addEventListener('DOMContentLoaded', () => {
  const sla = document.querySelectorAll('.sla-sidebar_content');
  const defaultImage = document.getElementById('default-image');
  const slaContent = document.querySelector('.sla-body_content');



  const slaDetails = {
      1:{
          number: '0000006',
          type: 'Use',
          category: 'Category 1',
          date: new Date(),
          department: 'Central Operations',
          status: 'Submitted',
          location: 'New Head Office'
      },
  
      2:{
          number: '0000005',
          type: 'Use',
          category: 'Category 2',
          date: new Date(),
          department: 'Central Operations',
          status: 'Submitted',
          location: 'New Head Office'
      }
  };

  const displayItemDetails = (details) => {
      document.getElementById('number').innerText = details.number
      document.getElementById('type').innerText = details.type;
      document.getElementById('category').innerText = details.category;
      document.getElementById('date').innerText = details.formattedDate;
      document.getElementById('required-date').innerText = details.formattedDate;
      document.getElementById('item-department').innerText = details.department;
      document.getElementById('item-status').innerText = details.status;
      document.getElementById('location').innerText = details.location;
  }
  
  sla.forEach(item => {
      item.addEventListener('click', () => {
          const itemId = item.dataset.id;
          const details = slaDetails[itemId];
  
          if (details) {
              defaultImage.style.display = 'none';
              slaContent.style.display = 'block';
              displayItemDetails(details)
          }
      })
  });
})
} catch (error) {
  console.log(error)
}


//Javascript logic for Category under Reference
try {
  document.addEventListener('DOMContentLoaded', () => {
    const sidebarContent = document.querySelector('.category-sidebar_contents');
    const categoryContent = document.querySelector('.category-sidebar_subContents');
    const subCategoryContent = document.querySelector('.subCategory-main_content');
    const loadMoreBtn = document.querySelector('.loadMoreBtn');
    const categoryCount = document.querySelector('.category-count');
    const subCategoryCount = document.querySelector('.subCategory-count');

    const categories = [
      {
        id: 1,
        name: 'Access Control',
        duration: "",
        description: '0000',
        status: 'Active',
        subcategory: [
          {
            id: 101,
            name: 'Automatic/Motorized Doors and Gates; (Supply, Installation, Maintenance and Repair)',
            description: '',
            status: 'Active',
          },
          { id: 102, name: 'Biometric Devices (Installation, Maintenance and Repair)', description: '', status: 'Active' },
          { id: 103, name: 'Body Scanner', description: '', status: 'Active' },
          { id: 104, name: 'Boom (Installation, Maintenance and Repair)', description: '', status: 'Active' },
          { id: 105, name: 'Electric Gates Services (Supply, Installation, Maintenance and Repair)', description: '', status: 'Active' },
          { id: 106, name: 'Explosive Detector (Supply, Installation, Maintenance and Repair)', description: '', status: 'Active' },
          { id: 107, name: 'Intruder Detection Systems (Supply, Installation, Maintenance and Repair)', description: '', status: 'Active' },
        ],
      },
      {
        id: 2,
        name: 'ADMIN - AMG CUG/Airtel Payment',
        duration: "",
        description: 'Admin',
        status: 'Active',
      },
      {
        id: 3,
        name: 'ADMIN Call/Data Recharge',
        duration: "",
        description: 'Admin',
        status: 'Active',
      },
      {
        id: 4,
        name: 'ADMIN HO Petty float',
        duration: "",
        description: 'Admin',
        status: 'Active',
        subcategory: [
          { id: 201, name: 'Building A', description: '3rd Floor', status: 'Active' },
        ],
      },
      {
        id: 5,
        name: 'Admin refreshment float',
        duration: "",
        description: 'Admin',
        status: 'Active',
        subcategory: [
          { id: 201, name: 'Building A', description: '3rd Floor', status: 'Active' },
        ],
      },
      {
        id: 6,
        name: 'Admin Stationaries / Beverages',
        duration: "",
        description: 'Admin',
        status: 'Active',
        subcategory: [
          { id: 201, name: 'Building A', description: '3rd Floor', status: 'Active' },
        ],
      },
      {
        id: 7,
        name: 'Administrative',
        duration: "",
        description: '0204',
        status: 'Active',
        subcategory: [
          { id: 201, name: 'Building A', description: '3rd Floor', status: 'Active' },
        ],
      },
      {
        id: 8,
        name: 'Aluminium Works',
        duration: "",
        description: 'AW',
        status: 'Active',
      },
    ];

    let categoryToShow = 10;

    function renderLocation() {
      sidebarContent.innerHTML = '';
      categories.slice(0, categoryToShow).forEach((order) => {
        const content = `
          <div class="category-sidebar_content" data-id="${order.id}">
            <div class="category-name">
              <span>${order.name}</span>
              <h6>${order.duration}</h6>
            </div>
            <div class="category-status">
              <h6>${order.description}</h6>
              <h6>${order.status}</h6>
            </div>
          </div>
        `;
        sidebarContent.insertAdjacentHTML('beforeend', content);
      });

      categoryCount.textContent = `Showing 1 - ${Math.min(categoryToShow, categories.length)} of ${categories.length}`;
    }

    function displayItemDetails(id) {
      const category = categories.find((item) => item.id === parseInt(id));

      if (category) {
        categoryContent.innerHTML = '';
        subCategoryContent.style.display = 'flex';

        if (category.subcategory && category.subcategory.length > 0) {
          category.subcategory.forEach((sub) => {
            const subCategoryHTML = `
              <div class="category-sidebar_content" data-id="${sub.id}" data-type="subcategory">
                <div class="category-name">
                  <span>${sub.name}</span>
                  <h6>${sub.status}</h6>
                </div>
                <div class="category-status">
                  <h6>${sub.description}</h6>
                </div>
              </div>
            `;
            categoryContent.insertAdjacentHTML('beforeend', subCategoryHTML);
          });
        } else {
          const noContentHTML = `
            <div class="no-content">
              <img src="./assets/img/in-empty-doc-card-icon.svg" alt="No Content" class="no-content-img">
              <h4>Oops!</h4>
              <p>Nothing in Subcategory</p>
            </div>
          `;
          categoryContent.insertAdjacentHTML('beforeend', noContentHTML);
        }
        buildingsCount.textContent = `Showing 1 - ${category.buildings.length} of ${category.buildings.length}`;
      }
    }

    sidebarContent.addEventListener('click', (event) => {
      const clickedItem = event.target.closest('.category-sidebar_content');
      if (clickedItem) {
        const itemId = clickedItem.dataset.id;
        displayItemDetails(itemId);
      }
    });

    loadMoreBtn.addEventListener('click', () => {
      locationToShow += 5;
      renderLocation();
    });

    renderLocation();
  });
} catch (error) {
  console.error('Error loading the app:', error);
}


