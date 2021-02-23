import {Store} from '../store';
import _ from 'lodash';
import {ProjectBaseData} from '../projectBaseData';
import {showNotification} from '../notifications';
import {projectSelected as ProjectSelected} from '../events';


const projectList = {
  id: 'project-list',
  type: 'x-template',
  definition: {
    template: `#project-list`,
    data() {
      return {
        projectList: [],
        permissions: {},
        dataStore: new ProjectBaseData(),
      };
    },
    created() {
      if (Store.get('current-user')) {
        this.loadData();
      }
      document.addEventListener('login', () => {
        this.loadData();
      });
    },
    mounted() {

    },
    computed: {},
    methods: {
      projectSelected(slug) {
        if (slug === Store.get('current-project')) {
          return;
        }
        Store.set('current-project', _.first(_.filter(this.projectList, p => p.slug === slug)).slug);
        showNotification(null, 'project ' + slug + ' selected');
        document.dispatchEvent(ProjectSelected);
      },
      loadData() {
        this.dataStore.getProjects(this.setProjects);
        this.dataStore.getPermissions(this.setPermissions);
      },
      setProjects(projectList) {
        this.projectList = projectList;
      },
      setPermissions(permissions) {
        this.permissions = permissions;
      },
      addNewProject() {
        showNotification('Make project', 'TODO');
      },
    },
  }
};

export {projectList};