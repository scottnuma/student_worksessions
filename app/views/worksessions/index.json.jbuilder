json.array!(@worksessions) do |worksession|
	if current_user.admin?
		json.extract! worksession, :id
		json.start worksession.begin_at
		json.end worksession.end_at
		json.title worksession.users.size().to_s
		if worksession.users.size() > 0
			json.color '#009900'
		end
		hash = {}
		worksession.bookings.each do |booking|
			hash[booking.user.team_name] = booking.notes
		end
		json.team_notes hash
		json.team_names worksession.users.collect { |user| user.team_name }.join(", ")

	end
end
