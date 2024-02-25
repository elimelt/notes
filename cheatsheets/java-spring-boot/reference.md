

### Annotations and their meanings



- `@SpringBootApplication`:
    marks the main class of the application. a combination of three other annotations: @Configuration, @EnableAutoConfiguration, and @ComponentScan.
- `@Configuration`:
    used to mark a class as a configuration class. This class will contain the bean definitions for the application context.
- `@EnableAutoConfiguration`:
    used to enable auto-configuration in the application. This annotation tells Spring Boot to start adding beans based on classpath settings, other beans, and various property settings.
- `@ComponentScan`:
    used to enable component scanning in the application. This allows Spring to scan packages to find and configure beans.
- `@RestController`:
    used to mark a class as a controller where every method returns a domain object instead of a view. It is shorthand for @Controller and @ResponseBody.
- `@RequestMapping`:
    used to map web requests onto specific handler classes and/or handler methods.
- `@RequestParam`:
    used to bind the web request parameter to a method parameter.