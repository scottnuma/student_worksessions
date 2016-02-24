== README

Running Locally

Make sure Ruby is installed on your system. Fire command prompt and run command

```
ruby -v
```
	
Make sure Rails is installed
rails -v

If you see Ruby and Rails version then you are good to start, other wise setup Ruby On Rails

```
gem install rails
```

Once done, clone the git repository
```
git clone https://github.com/pioneers/student_worksessions.git
```
Go into app directory
```
cd student_worksessions
```
Install all dependencies
```
bundle install
```
Create db and migrate schema
```
rake db:create
rake db:migrate
```
Now run your application
```
rails s
```
It should be hosted on localhost:3000 on your local machine

